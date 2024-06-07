from .models import CustomUser
import logging

logger = logging.getLogger(__name__)

def user_context(request):
    if request.user.is_authenticated:
        try:
            user = request.user
            user_departments = user.departments.all()
            headed_departments = user.headed_departments.all()
            is_superior = headed_departments.exists()
            return {
                'user_departments': user_departments,
                'headed_departments': headed_departments,
                'is_superior': is_superior,
            }
        except AttributeError as e:
            logger.error(f"Error in user_context: {e}")
    return {}
