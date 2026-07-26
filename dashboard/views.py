from django.shortcuts import render

from dashboard.services.dashboard_facade import DashboardFacade


def dashboard_home(request):
    """
    View principal do Dashboard.
    """

    facade = DashboardFacade()

    context = facade.get_dashboard_data()

    return render(
        request,
        "dashboard/home.html",
        context,
    )


# Alias para compatibilidade com versões anteriores
home = dashboard_home