from .models import CustomUser
import logging

logger = logging.getLogger(__name__)

def user_context(request):
    if request.user.is_authenticated:
        try:
            user = CustomUser.objects.get(pk=request.user.pk)
            user_departments = user.departments.all()
            headed_departments = user.headed_departments.all()
            is_superior = headed_departments.exists()
            return {
                'user_departments': user_departments,
                'headed_departments': headed_departments,
                'is_superior': is_superior,
            }
        except CustomUser.DoesNotExist:
            logger.error(f"CustomUser matching query does not exist.")
        except AttributeError as e:
            logger.error(f"Error in user_context: {e}")
    return {}