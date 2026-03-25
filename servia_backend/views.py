from django.http import HttpResponse

def home(request):
    return HttpResponse("Hello Servia AI")

def health(request):
    return HttpResponse("ok")
    