/*
=========================================
AgroClima Café

KPI Cards
=========================================
*/

document.addEventListener("DOMContentLoaded", () => {

    const cards = document.querySelectorAll(".kpi-card");

    cards.forEach((card, index) => {

        card.style.opacity = 0;
        card.style.transform = "translateY(20px)";

        setTimeout(() => {

            card.style.transition = "all .45s ease";

            card.style.opacity = 1;

            card.style.transform = "translateY(0)";

        }, index * 120);

    });

});