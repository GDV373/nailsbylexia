from django.shortcuts import render


def home(request):
    return render(request, "pages/home.html")


def services_page(request):
    return render(request, "pages/services.html")


def contact_page(request):
    return render(request, "pages/contact.html")