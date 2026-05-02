from django.shortcuts import render

from services.models import NailService


def home(request):
    return render(request, "pages/home.html")


def services_page(request):
    nail_services = NailService.objects.filter(
        active=True,
        service_area="nails"
    ).order_by("price", "name")

    toe_services = NailService.objects.filter(
        active=True,
        service_area="toes"
    ).order_by("price", "name")

    return render(request, "pages/services.html", {
        "nail_services": nail_services,
        "toe_services": toe_services,
    })


def contact_page(request):
    return render(request, "pages/contact.html")