from django.core.management.base import BaseCommand
import pymssql
from datetime import datetime
from useri.models import CustomUser, Role
from django.core.exceptions import ValidationError
import logging


class Command(BaseCommand):
    help = 'Update users from MSSQL database'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def convert_date(self, date_string):
        """
        Convert date string from 'DD/MM/YYYY' or 'DD-MM-YYYY' format to 'YYYY-MM-DD' format.
        Returns None if the date_string is empty or cannot be parsed.
        Logs error if the date format is invalid.
        """
        if not date_string or not date_string.strip():
            return None

        for date_format in ('%d/%m/%Y', '%d-%m-%Y'):
            try:
                self.logger.info(f"Processing date string: {date_string}")
                return datetime.strptime(date_string, date_format).strftime('%Y-%m-%d')
            except ValueError as e:
                self.logger.error(f"Error processing date string '{date_string}': {e}")

        # Log the date string causing the error
        self.logger.error(f"Unrecognized date format: {date_string}")

        return None

    def handle(self, *args, **kwargs):
        # Get the default role
        default_role, _ = Role.objects.get_or_create(name='User')

        conn = pymssql.connect(server='172.21.30.101\MANTRA2017', user='Report', password='Report@123',
                               database='JSW_Dharamtar')
        cursor = conn.cursor(as_dict=True)

        # Fetch data from MSSQL attendance database
        cursor.execute('SELECT * FROM dbo.view_EmployeeMaster_Report_staff')

        for row in cursor.fetchall():
            # Get or create user
            user, created = CustomUser.objects.get_or_create(username=row['EMPLOYEE ID'], defaults={'role': default_role})

            # Update user fields from MSSQL data
            user.employee_id = row['EMPLOYEE ID']
            user.employee_name = row['EMPLOYEE  NAME']
            user.gender = row['GENDER']

            # Convert date format for DATE OF BIRTH, DATE OF JOINING, WORK ORDER EXPIRY DATE, and CARD VALIDITY
            date_fields = ['DATE OF BIRTH', 'DATE OF JOINING', 'WORK ORDER EXPIRY DATE', 'CARD VALIDITY', 'DATE OF LEAVING']
            for field in date_fields:
                try:
                    date_value = self.convert_date(row[field])
                    if date_value is not None:
                        setattr(user, field.lower().replace(' ', '_'), date_value)
                except ValidationError as e:
                    print(e)

            # Add more fields from your data model
            user.blood_group = row.get('BLOOD GROUP', '')
            user.marital_status = row.get('MARITAL STATUS', '')
            user.nationality = row.get('NATIONALITY', '')
            user.caste = row.get('CASTE', '')
            user.origin = row.get('ORIGIN', '')
            user.weight = row.get('WEIGHT', 0)
            user.height = row.get('HEIGHT', 0)
            user.designation = row.get('DESIGNATION', '')
            user.department = row.get('DEPARTMENT', '')
            user.work_order_no = row.get('WORK ORDER NO', '')
            user.work_order_expiry_date = self.convert_date(row.get('WORK ORDER EXPIRY DATE', ''))
            user.item_code = row.get('ITEM CODE', '')
            user.contractor_name = row.get('CONTRACTOR NAME', '')
            user.sub_contractor_name = row.get('SUB CONTRACTOR NAME', '')
            user.under_sub_contractor_name = row.get('UNDER SUB CONTRACTOR NAME', '')
            user.category = row.get('CATEGORY', '')
            user.pf_code = row.get('PF CODE', '')
            user.uan_no_pf = row.get('UAN NO. (PF)', '')
            user.pf_no = row.get('PF NO', '')
            user.pan_no = row.get('PANNO', '')
            user.lic_policy_no = row.get('LIC POLICY NO', '')
            user.shift_group = row.get('SHIFT GROUP', '')
            user.section = row.get('SECTION', '')
            user.identification_mark_1 = row.get('IDENTIFICATION MARK 1', '')
            user.identification_mark_2 = row.get('IDENTIFICATION MARK 2', '')
            user.email = row.get('EMAIL ID', '')
            user.contact_no = row.get('CONTACT NO', '')
            user.emergency_contact_person = row.get('EMERGENCY CONTACT PERSON', '')
            user.emergency_contact_no = row.get('EMERGENCY CONTACT NO', '')
            user.date_of_leaving = self.convert_date(row.get('DATE OF LEAVING', ''))
            user.card_validity = self.convert_date(row.get('CARD VALIDITY', ''))
            user.card_status = row.get('CARD STATUS', '')
            user.address = row.get('Address', '')
            user.pin_code = row.get('PinCode', '')
            user.card_active_status = row.get('CardActiveStatus', '')
            user.taluka = row.get('Taluka', '')
            user.district = row.get('District', '')
            user.state = row.get('State', '')
            user.per_address = row.get('Per.Address', '')
            user.per_pin_code = row.get('Per.PinCode', '')
            user.per_taluka = row.get('Per.Taluka', '')
            user.per_district = row.get('Per.District', '')
            user.per_state = row.get('Per.State', '')

            # Set default password
            user.set_password('jsw@12345')

            # Save the user
            user.save()

        # Close the database connection
        conn.close()

        self.stdout.write(self.style.SUCCESS('Users updated successfully'))
