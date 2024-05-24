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

        conn = pymssql.connect(server='172.21.30.101\MANTRA2017', user='Report', password='Report@123', database='JSW_Dharamtar')
        cursor = conn.cursor(as_dict=True)

        # Fetch data from MSSQL attendance database
        cursor.execute('SELECT * FROM dbo.view_EmployeeMaster_Report_Associates')

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
                        user.__dict__[field.lower().replace(' ', '_')] = date_value
                except ValidationError as e:
                    print(e)

            # Add more fields from your data model
            user.blood_group = row['BLOOD GROUP']
            user.marital_status = row['MARITAL STATUS']
            user.weight = row['WEIGHT']
            user.height = row['HEIGHT']
            user.designation = row['DESIGNATION']
            user.department = row['DEPARTMENT']
            user.grade = row['GRADE']
            user.work_order_no = row['WORK ORDER NO']
            user.item_code = row['ITEM CODE']
            user.contractor_name = row['CONTRACTOR NAME']
            user.sub_contractor_name = row['SUB CONTRACTOR NAME']
            user.under_sub_contractor_name = row['UNDER SUB CONTRACTOR NAME']
            user.category = row['CATEGORY']
            user.pf_code = row['PF CODE']
            user.uan_no_pf = row['UAN NO. (PF)']
            user.pf_no = row['PF NO']
            user.pan_no = row['PANNO']
            user.lic_policy_no = row['LIC POLICY NO']
            user.shift_group = row['SHIFT GROUP']
            user.section = row['SECTION']
            user.identification_mark_1 = row['IDENTIFICATION MARK 1']
            user.identification_mark_2 = row['IDENTIFICATION MARK 2']
            user.email = row['EMAIL ID']
            user.contact_no = row['CONTACT NO']
            user.emergency_contact_person = row['EMERGENCY CONTACT PERSON']
            user.emergency_contact_no = row['EMERGENCY CONTACT NO']
            user.card_active_status = row['CardActiveStatus']
            user.card_status = row['CARD STATUS']
            user.esi_no = row['ESINo']
            user.address = row['Address']
            user.pin_code = row['PinCode']
            user.taluka = row['Taluka']
            user.district = row['District']
            user.state = row['State']
            user.per_address = row['Per.Address']
            user.per_pin_code = row['Per.PinCode']
            user.per_taluka = row['Per.Taluka']
            user.per_district = row['Per.District']
            user.per_state = row['Per.State']
            user.poi = row['POI']
            user.poino = row['POINO']
            user.poa = row['POA']
            user.poano = row['POANO']
            user.bank_name = row['BankName']
            user.branch_name = row['BranchName']
            user.account_number = row['AccountNumber']

            # Set default password
            user.set_password('jsw@12345')

            # Save the user
            user.save()

        # Close the database connection
        conn.close()

        self.stdout.write(self.style.SUCCESS('Users updated successfully'))
