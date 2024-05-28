from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json

def create_form(request):
    return render(request, 'formbuilder/create.html')

@csrf_exempt
def preview_form(request):
    if request.method == 'POST':
        form_data = json.loads(request.POST['form_data'])
        return render(request, 'formbuilder/preview.html', {'form_data': form_data})
    return render(request, 'formbuilder/error.html', {'message': 'Invalid request method.'})
