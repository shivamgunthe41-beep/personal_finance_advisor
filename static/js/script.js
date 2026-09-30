/* =========================================================
   PERSONAL FINANCE ADVISOR BOT
   Frontend JavaScript
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    const financeForm = document.getElementById("financeForm");
    const analyseButton = document.getElementById("analyseButton");
    const resultsSection = document.getElementById("resultsSection");
    const resultsSummary = document.getElementById("resultsSummary");

    const financialSummary =
        document.getElementById("financialSummary");

    const budgetContainer =
        document.getElementById("budgetContainer");

    const analysisContainer =
        document.getElementById("analysisContainer");

    const suggestionsContainer =
        document.getElementById("suggestionsContainer");


    /* =====================================================
       FORM SUBMISSION
    ===================================================== */

    financeForm.addEventListener("submit", async (event) => {

        event.preventDefault();

        clearError();

        const incomeInput =
            document.getElementById("income");

        const income =
            Number(incomeInput.value);

        if (!income || income <= 0) {
            showError(
                "Please enter a valid monthly income."
            );

            incomeInput.focus();
            return;
        }


        /* =================================================
           COLLECT EXPENSES
        ================================================= */

        const expenseNames = [
            "rent",
            "food",
            "transport",
            "dining",
            "entertainment",
            "utilities",
            "savings",
            "other"
        ];

        const expenses = {};

        let totalExpenses = 0;

        expenseNames.forEach((name) => {

            const input =
                document.getElementById(name);

            const value =
                Number(input.value) || 0;

            if (value > 0) {
                expenses[name] = value;
                totalExpenses += value;
            }

        });


        if (totalExpenses <= 0) {

            showError(
                "Please enter at least one expense category."
            );

            document.getElementById("rent").focus();

            return;
        }


        /* =================================================
           CHECK EXPENSES AGAINST INCOME
        ================================================= */

        if (totalExpenses > income) {

            const proceed =
                confirm(
                    "Your total expenses are higher than your income. " +
                    "Do you still want the AI advisor to analyse them?"
                );

            if (!proceed) {
                return;
            }
        }


        /* =================================================
           GET GOAL
        ================================================= */

        const goal =
            document.getElementById("goal").value;


        /* =================================================
           PREPARE REQUEST
        ================================================= */

        const requestData = {
            income: income,
            expenses: expenses,
            goal: goal
        };


        /* =================================================
           LOADING STATE
        ================================================= */

        setLoading(true);


        try {

            const response =
                await fetch("/analyse", {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(requestData)
                });


            let data;

            try {
                data = await response.json();
            } catch (jsonError) {

                throw new Error(
                    "The server returned an invalid response."
                );
            }


            /* =============================================
               SERVER ERROR
            ============================================= */

            if (!response.ok || !data.success) {

                throw new Error(
                    data.error ||
                    "Unable to analyse your finances."
                );
            }


            /* =============================================
               RENDER RESULTS
            ============================================= */

            renderResults(data);


        } catch (error) {

            console.error(
                "Finance analysis error:",
                error
            );

            showError(
                error.message ||
                "Something went wrong. Please try again."
            );

        } finally {

            setLoading(false);

        }

    });


    /* =====================================================
       LOADING STATE
    ===================================================== */

    function setLoading(isLoading) {

        if (isLoading) {

            analyseButton.disabled = true;

            analyseButton.classList.add("loading");

            analyseButton.setAttribute(
                "aria-busy",
                "true"
            );

        } else {

            analyseButton.disabled = false;

            analyseButton.classList.remove("loading");

            analyseButton.removeAttribute(
                "aria-busy"
            );

        }

    }


    /* =====================================================
       RENDER ALL RESULTS
    ===================================================== */

    function renderResults(data) {

        clearError();


        /* ================================================
           CLEAR OLD RESULTS
        ================================================= */

        financialSummary.innerHTML = "";
        budgetContainer.innerHTML = "";
        analysisContainer.innerHTML = "";
        suggestionsContainer.innerHTML = "";


        /* ================================================
           SUMMARY
        ================================================= */

        renderFinancialSummary(
            data.financial_summary
        );


        /* ================================================
           BUDGET
        ================================================= */

        renderBudget(
            data.budget
        );


        /* ================================================
           ANALYSIS
        ================================================= */

        renderAnalysis(
            data.analysis
        );


        /* ================================================
           SUGGESTIONS
        ================================================= */

        renderSuggestions(
            data.suggestions
        );


        /* ================================================
           SUMMARY TEXT
        ================================================= */

        if (data.summary) {

            resultsSummary.textContent =
                data.summary;

        } else {

            resultsSummary.textContent =
                "Your personalized financial recommendations are ready.";

        }


        /* ================================================
           SHOW RESULTS
        ================================================= */

        resultsSection.classList.add(
            "visible"
        );


        /* ================================================
           SMOOTH SCROLL
        ================================================= */

        setTimeout(() => {

            resultsSection.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        }, 100);

    }


    /* =====================================================
       FINANCIAL SUMMARY
    ===================================================== */

    function renderFinancialSummary(summary) {

        if (!summary) {
            return;
        }


        const cards = [

            {
                label: "Monthly Income",
                value: formatCurrency(summary.income),
                subtitle: "Total monthly income",
                icon: "fa-wallet"
            },

            {
                label: "Total Expenses",
                value: formatCurrency(summary.total_expenses),
                subtitle: "Current monthly spending",
                icon: "fa-receipt"
            },

            {
                label: "Remaining",
                value: formatCurrency(summary.remaining),
                subtitle: summary.remaining >= 0
                    ? "Available after expenses"
                    : "Expenses exceed income",
                icon: summary.remaining >= 0
                    ? "fa-arrow-trend-up"
                    : "fa-triangle-exclamation"
            },

            {
                label: "Savings Rate",
                value: formatPercentage(
                    summary.planned_savings_percentage ??
                    summary.savings_percentage ??
                    0
                ),
                subtitle: "Based on your income",
                icon: "fa-piggy-bank"
            }

        ];


        cards.forEach((card) => {

            const element =
                document.createElement("div");

            element.className =
                "summary-card";


            element.innerHTML = `
                <div class="summary-card-top">

                    <span class="summary-card-label">
                        ${escapeHTML(card.label)}
                    </span>

                    <div class="summary-card-icon">
                        <i class="fa-solid ${card.icon}"></i>
                    </div>

                </div>

                <div class="summary-card-value">
                    ${escapeHTML(card.value)}
                </div>

                <div class="summary-card-subtitle">
                    ${escapeHTML(card.subtitle)}
                </div>
            `;


            financialSummary.appendChild(element);

        });

    }


    /* =====================================================
       BUDGET
    ===================================================== */

    function renderBudget(budget) {

        if (!Array.isArray(budget) || budget.length === 0) {

            budgetContainer.innerHTML = `
                <div class="empty-result">
                    No budget recommendations were returned.
                </div>
            `;

            return;
        }


        budget.forEach((item) => {

            const category =
                item.category ||
                item.name ||
                "Category";

            const amount =
                Number(
                    item.amount ??
                    item.recommended ??
                    item.recommended_amount ??
                    0
                );

            const percentage =
                Number(
                    item.percentage ??
                    item.percent ??
                    0
                );


            const safePercentage =
                Math.min(
                    100,
                    Math.max(0, percentage)
                );


            const element =
                document.createElement("div");

            element.className =
                "budget-item";


            element.innerHTML = `
                <div class="budget-item-top">

                    <div class="budget-category">

                        <span class="budget-category-icon">
                            <i class="fa-solid ${getCategoryIcon(category)}"></i>
                        </span>

                        <span>
                            ${escapeHTML(category)}
                        </span>

                    </div>

                    <span class="budget-amount">
                        ${formatCurrency(amount)}
                    </span>

                </div>

                <div class="progress-track">

                    <div
                        class="progress-bar"
                        style="width: ${safePercentage}%"
                    ></div>

                </div>

                <div class="budget-meta">

                    <span>
                        Recommended allocation
                    </span>

                    <span>
                        ${safePercentage.toFixed(0)}%
                    </span>

                </div>
            `;


            budgetContainer.appendChild(element);

        });

    }


    /* =====================================================
       SPENDING ANALYSIS
    ===================================================== */

    function renderAnalysis(analysis) {

        if (!Array.isArray(analysis) || analysis.length === 0) {

            analysisContainer.innerHTML = `
                <div class="empty-result">
                    No spending analysis was returned.
                </div>
            `;

            return;
        }


        analysis.forEach((item) => {

            const category =
                item.category ||
                item.name ||
                "Category";

            const percentage =
                Number(
                    item.percentage ??
                    item.percent ??
                    0
                );

            const status =
                String(
                    item.status ||
                    getStatusFromPercentage(percentage)
                ).toLowerCase();


            const description =
                item.description ||
                item.message ||
                item.analysis ||
                "";


            let statusClass =
                "status-success";

            let statusText =
                "On track";


            if (
                status.includes("over") ||
                status.includes("high") ||
                status.includes("danger")
            ) {

                statusClass =
                    "status-danger";

                statusText =
                    "Overspending";

            } else if (
                status.includes("warning") ||
                status.includes("moderate")
            ) {

                statusClass =
                    "status-warning";

                statusText =
                    "Watch";

            }


            const element =
                document.createElement("div");

            element.className =
                `analysis-chip ${statusClass}`;


            element.innerHTML = `
                <div class="analysis-chip-top">

                    <span class="analysis-category">
                        ${escapeHTML(category)}
                    </span>

                    <span class="analysis-status">
                        ${escapeHTML(statusText)}
                    </span>

                </div>

                <div class="analysis-percentage">
                    ${percentage.toFixed(1)}%
                </div>

                <div class="analysis-description">
                    ${escapeHTML(description)}
                </div>
            `;


            analysisContainer.appendChild(element);

        });

    }


    /* =====================================================
       SAVING SUGGESTIONS
    ===================================================== */

    function renderSuggestions(suggestions) {

        if (!Array.isArray(suggestions) ||
            suggestions.length === 0) {

            suggestionsContainer.innerHTML = `
                <li class="suggestion-item">
                    <div class="suggestion-content">
                        No saving suggestions were returned.
                    </div>
                </li>
            `;

            return;
        }


        suggestions.forEach((suggestion) => {

            let text = "";
            let amount = "";


            if (typeof suggestion === "string") {

                text = suggestion;

            } else if (
                suggestion &&
                typeof suggestion === "object"
            ) {

                text =
                    suggestion.text ||
                    suggestion.suggestion ||
                    suggestion.description ||
                    suggestion.action ||
                    "";

                const numericAmount =
                    Number(
                        suggestion.amount ??
                        suggestion.savings ??
                        suggestion.potential_saving ??
                        0
                    );


                if (numericAmount > 0) {

                    amount =
                        `Potential saving: ${formatCurrency(
                            numericAmount
                        )}`;

                }

            }


            if (!text) {
                text = "Review this area of your spending.";
            }


            const element =
                document.createElement("li");

            element.className =
                "suggestion-item";


            element.innerHTML = `
                <div class="suggestion-content">

                    ${escapeHTML(text)}

                    ${
                        amount
                            ? `
                                <span class="suggestion-amount">
                                    ${escapeHTML(amount)}
                                </span>
                              `
                            : ""
                    }

                </div>
            `;


            suggestionsContainer.appendChild(element);

        });

    }


    /* =====================================================
       CATEGORY ICONS
    ===================================================== */

    function getCategoryIcon(category) {

        const name =
            String(category).toLowerCase();


        if (name.includes("rent") ||
            name.includes("housing")) {
            return "fa-house";
        }

        if (name.includes("food")) {
            return "fa-utensils";
        }

        if (name.includes("transport")) {
            return "fa-car";
        }

        if (name.includes("dining")) {
            return "fa-bowl-food";
        }

        if (name.includes("entertainment")) {
            return "fa-film";
        }

        if (name.includes("utilit")) {
            return "fa-bolt";
        }

        if (name.includes("saving")) {
            return "fa-piggy-bank";
        }

        if (name.includes("invest")) {
            return "fa-chart-line";
        }

        return "fa-wallet";
    }


    /* =====================================================
       STATUS
    ===================================================== */

    function getStatusFromPercentage(percentage) {

        if (percentage > 30) {
            return "overspending";
        }

        if (percentage > 20) {
            return "warning";
        }

        return "on track";
    }


    /* =====================================================
       CURRENCY
    ===================================================== */

    function formatCurrency(value) {

        const number =
            Number(value) || 0;


        return new Intl.NumberFormat(
            "en-IN",
            {
                style: "currency",
                currency: "INR",
                maximumFractionDigits: 0
            }
        ).format(number);
    }


    /* =====================================================
       PERCENTAGE
    ===================================================== */

    function formatPercentage(value) {

        const number =
            Number(value) || 0;

        return `${number.toFixed(1)}%`;
    }


    /* =====================================================
       ERROR MESSAGE
    ===================================================== */

    function showError(message) {

        clearError();


        const error =
            document.createElement("div");

        error.id =
            "financeError";

        error.className =
            "error-message";


        error.setAttribute(
            "role",
            "alert"
        );


        error.innerHTML = `
            <i class="fa-solid fa-circle-exclamation"></i>

            <span>
                ${escapeHTML(message)}
            </span>
        `;


        financeForm.appendChild(error);


        error.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

    }


    function clearError() {

        const existing =
            document.getElementById(
                "financeError"
            );


        if (existing) {
            existing.remove();
        }

    }


    /* =====================================================
       HTML ESCAPING
       Prevents AI-generated text from becoming HTML.
    ===================================================== */

    function escapeHTML(value) {

        const div =
            document.createElement("div");

        div.textContent =
            String(value ?? "");

        return div.innerHTML;
    }


    /* =====================================================
       INITIAL STATE
    ===================================================== */

    resultsSection.classList.remove(
        "visible"
    );

});