from django.shortcuts import render

from dashboard.services.dashboard_service import DashboardService


def home(request):

    context = DashboardService().get_dashboard()

    return render(

        request,

        "dashboard/home.html",

        context

    )