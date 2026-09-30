import os
import json
import re
import time

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY was not found. Please check your .env file."
    )


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)

MODEL_NAME = "gemini-3.5-flash-lite"


# ============================================================
# FINANCIAL CATEGORY GUIDELINES
# ============================================================

CATEGORY_TIPS = {
    "rent": {
        "recommended": 30,
        "description": "Housing costs should generally stay around 30% or less of income."
    },

    "food": {
        "recommended": 15,
        "description": "Food expenses should generally remain below 15% of income."
    },

    "transport": {
        "recommended": 10,
        "description": "Transportation costs should generally remain within 10% of income."
    },

    "dining": {
        "recommended": 5,
        "description": "Dining expenses should be controlled and kept relatively low."
    },

    "entertainment": {
        "recommended": 8,
        "description": "Entertainment spending should generally remain around 5–8% of income."
    },

    "utilities": {
        "recommended": 10,
        "description": "Utilities should be monitored and kept within a reasonable portion of income."
    },

    "savings": {
        "recommended": 20,
        "description": "A savings allocation of at least 20% is a useful general target when possible."
    },

    "other": {
        "recommended": 10,
        "description": "Other expenses should be tracked carefully."
    }
}


# ============================================================
# FINANCIAL GOALS
# ============================================================

GOAL_DESCRIPTIONS = {
    "emergency fund":
        "Build a sufficient emergency fund for unexpected expenses.",

    "vacation":
        "Save systematically toward a planned vacation.",

    "gadget purchase":
        "Save toward purchasing a desired gadget without unnecessary debt.",

    "investment":
        "Build savings and consider suitable long-term investment planning."
}


# ============================================================
# NUMBER CLEANING
# ============================================================

def clean_number(value):
    """
    Convert a value into a safe non-negative number.
    """

    try:

        if value is None:
            return 0.0

        if isinstance(value, str):
            value = value.replace(",", "").strip()

        number = float(value)

        if number < 0:
            return 0.0

        return number

    except (ValueError, TypeError):

        return 0.0


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text):
    """
    Extract valid JSON from Gemini's response.

    Supports:
    1. Direct JSON
    2. Markdown JSON code blocks
    3. JSON embedded inside other text
    """

    if not text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    text = text.strip()

    # --------------------------------------------------------
    # METHOD 1: DIRECT JSON
    # --------------------------------------------------------

    try:

        return json.loads(text)

    except json.JSONDecodeError:

        pass

    # --------------------------------------------------------
    # METHOD 2: MARKDOWN CODE BLOCK
    # --------------------------------------------------------

    code_block_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if code_block_match:

        try:

            return json.loads(
                code_block_match.group(1)
            )

        except json.JSONDecodeError:

            pass

    # --------------------------------------------------------
    # METHOD 3: FIND JSON OBJECT
    # --------------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:

        json_text = text[
            start:end + 1
        ]

        try:

            return json.loads(
                json_text
            )

        except json.JSONDecodeError:

            pass

    raise ValueError(
        "Could not extract valid JSON from Gemini response."
    )


# ============================================================
# VALIDATE AI RESPONSE
# ============================================================

def validate_ai_response(data):
    """
    Validate the structure returned by Gemini.
    """

    if not isinstance(data, dict):

        raise ValueError(
            "AI response is not a valid object."
        )

    required_keys = [
        "budget",
        "analysis",
        "suggestions"
    ]

    for key in required_keys:

        if key not in data:

            raise ValueError(
                f"AI response is missing required field: {key}"
            )

    if not isinstance(
        data["budget"],
        list
    ):

        raise ValueError(
            "Budget must be a list."
        )

    if not isinstance(
        data["analysis"],
        list
    ):

        raise ValueError(
            "Analysis must be a list."
        )

    if not isinstance(
        data["suggestions"],
        list
    ):

        raise ValueError(
            "Suggestions must be a list."
        )

    if "summary" not in data:

        data["summary"] = (
            "Your financial analysis has been completed."
        )

    return data


# ============================================================
# BUILD AI PROMPT
# ============================================================

def build_prompt(
    income,
    expenses,
    goal
):
    """
    Build the structured financial-analysis prompt.
    """

    expense_lines = []

    for category, amount in expenses.items():

        tip = CATEGORY_TIPS.get(
            category,
            {
                "recommended": 10,
                "description": "Review this category carefully."
            }
        )

        expense_lines.append(
            f"- {category.title()}: "
            f"₹{amount:,.2f} "
            f"(Recommended: approximately "
            f"{tip['recommended']}%)"
        )

    expense_text = "\n".join(
        expense_lines
    )

    total_expenses = sum(
        expenses.values()
    )

    remaining = income - total_expenses

    # --------------------------------------------------------
    # IMPORTANT:
    # Savings entered by the user is planned savings.
    # Remaining is money left after ALL entered expenses.
    # --------------------------------------------------------

    planned_savings = expenses.get(
        "savings",
        0
    )

    planned_savings_percentage = (
        (planned_savings / income) * 100
        if income > 0
        else 0
    )

    remaining_percentage = (
        (remaining / income) * 100
        if income > 0
        else 0
    )

    goal_description = GOAL_DESCRIPTIONS.get(
        goal.lower(),
        "Improve overall financial stability and savings."
    )

    prompt = f"""
You are a professional personal finance advisor.

Analyze the user's monthly financial information and provide
clear, practical and responsible financial guidance.

IMPORTANT RULES:

- Return ONLY valid JSON.
- Do not return Markdown.
- Do not return text outside the JSON.
- Monetary values must be numbers.
- Use Indian Rupees.
- Do not invent expenses.
- Use the actual values supplied by the user.
- Keep recommendations practical.
- Do not guarantee investment returns.
- Do not provide risky or speculative investment instructions.

============================================================
USER FINANCIAL INFORMATION
============================================================

Monthly Income:
₹{income:,.2f}

Expenses:

{expense_text}

Total Entered Expenses:
₹{total_expenses:,.2f}

Remaining After Entered Expenses:
₹{remaining:,.2f}

Remaining Percentage:
{remaining_percentage:.2f}%

Planned Savings Entered by User:
₹{planned_savings:,.2f}

Planned Savings Percentage:
{planned_savings_percentage:.2f}%

Financial Goal:
{goal}

Goal Description:
{goal_description}

============================================================
IMPORTANT SAVINGS INTERPRETATION
============================================================

The "savings" expense entered by the user represents
PLANNED SAVINGS.

The "remaining" amount represents money that is still
unallocated after all entered expenses.

Do NOT call the planned savings percentage the overall
remaining/savings rate.

If the user entered ₹10,000 savings from ₹50,000 income,
planned savings are 20%.

If total entered expenses are ₹37,000,
the remaining amount is ₹13,000, which is 26% of income.

Explain these separately when relevant.

============================================================
CATEGORY GUIDELINES
============================================================

Rent:
Approximately 30% or less.

Food:
Approximately below 15%.

Transport:
Approximately 10% or less.

Dining:
Keep controlled.

Entertainment:
Approximately 5–8%.

Utilities:
Keep within a reasonable portion of income.

Savings:
Aim for at least 20% when possible.

Other:
Review carefully.

============================================================
REQUIRED JSON STRUCTURE
============================================================

Return exactly this structure:

{{
    "budget": [
        {{
            "category": "Rent",
            "amount": 12000,
            "percentage": 24,
            "recommended_percentage": 30,
            "status": "on track",
            "description": "Housing spending is within the recommended range."
        }}
    ],

    "analysis": [
        {{
            "category": "Rent",
            "percentage": 24,
            "status": "on track",
            "description": "Housing expenses are within the recommended range."
        }}
    ],

    "suggestions": [
        {{
            "text": "Consider directing ₹2000 of the remaining amount toward your emergency fund.",
            "amount": 2000
        }}
    ],

    "summary": "Your overall financial summary."
}}

============================================================
BUDGET REQUIREMENTS
============================================================

For every provided expense category:

- Use the actual expense amount.
- Calculate percentage of monthly income.
- Provide a reasonable recommended percentage.
- Give one status.

Allowed statuses:

"on track"
"high"
"low"
"needs attention"

============================================================
ANALYSIS REQUIREMENTS
============================================================

For every provided expense category:

- Calculate percentage of income.
- Explain whether the spending is reasonable.
- Keep the explanation concise.
- Compare it with the relevant guideline.

============================================================
SUGGESTION REQUIREMENTS
============================================================

Provide 3–5 practical suggestions.

Suggestions must:

- Be based on actual spending.
- Consider the selected financial goal.
- Mention realistic amounts where useful.
- Avoid guarantees.
- Help improve budgeting and saving habits.

============================================================
SUMMARY REQUIREMENTS
============================================================

The summary must:

- Mention total expenses.
- Mention remaining amount.
- Distinguish planned savings from remaining money.
- Mention the selected financial goal.
- Be concise and easy to understand.
"""


    return prompt


# ============================================================
# GENERATE FINANCIAL ADVICE
# ============================================================

def generate_financial_advice(prompt):
    """
    Generate financial advice using Gemini.

    Temporary 503 and rate-limit errors are retried automatically.
    """

    max_attempts = 3

    for attempt in range(
        max_attempts
    ):

        try:

            print(
                f"\nGemini request attempt "
                f"{attempt + 1}/{max_attempts}"
            )

            response = client.models.generate_content(

                model=MODEL_NAME,

                contents=prompt,

                config=types.GenerateContentConfig(

                    max_output_tokens=2048,

                    response_mime_type="application/json",

                    automatic_function_calling={
                        "disable": True
                    }
                )
            )

            if not response:

                raise RuntimeError(
                    "Gemini returned no response."
                )

            if not response.text:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            print(
                "Gemini response received successfully."
            )

            data = extract_json(
                response.text
            )

            return validate_ai_response(
                data
            )

        except Exception as e:

            error_text = str(e)

            print(
                f"Gemini attempt "
                f"{attempt + 1}/{max_attempts} failed:"
            )

            print(
                error_text
            )

            # ------------------------------------------------
            # TEMPORARY SERVICE / RATE LIMIT ERRORS
            # ------------------------------------------------

            temporary_error = (

                "503" in error_text

                or

                "UNAVAILABLE" in error_text

                or

                "429" in error_text

                or

                "RESOURCE_EXHAUSTED" in error_text
            )

            if temporary_error:

                if attempt < max_attempts - 1:

                    wait_time = 2 ** attempt

                    print(
                        f"Temporary Gemini error. "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

            # ------------------------------------------------
            # OTHER ERROR
            # ------------------------------------------------

            raise

    raise RuntimeError(
        "Gemini service is temporarily unavailable."
    )


# ============================================================
# HOME ROUTE
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# ANALYSE ROUTE
# ============================================================

@app.route(
    "/analyse",
    methods=["POST"]
)
def analyse():

    try:

        # ----------------------------------------------------
        # READ JSON REQUEST
        # ----------------------------------------------------

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "error": "No financial data was received."
            }), 400

        # ----------------------------------------------------
        # INCOME
        # ----------------------------------------------------

        income = clean_number(
            data.get("income")
        )

        if income <= 0:

            return jsonify({
                "success": False,
                "error": "Please enter a valid monthly income."
            }), 400

        if income > 1000000000:

            return jsonify({
                "success": False,
                "error": "Income value is too large."
            }), 400

        # ----------------------------------------------------
        # EXPENSES
        # ----------------------------------------------------

        raw_expenses = data.get(
            "expenses",
            {}
        )

        if not isinstance(
            raw_expenses,
            dict
        ):

            return jsonify({
                "success": False,
                "error": "Invalid expense data."
            }), 400

        expenses = {}

        for category, value in raw_expenses.items():

            amount = clean_number(
                value
            )

            if amount > 0:

                expenses[
                    str(category).lower()
                ] = amount

        if not expenses:

            return jsonify({
                "success": False,
                "error": "Please enter at least one expense."
            }), 400

        # ----------------------------------------------------
        # EXPENSE LIMIT CHECK
        # ----------------------------------------------------

        for category, amount in expenses.items():

            if amount > 1000000000:

                return jsonify({
                    "success": False,
                    "error": (
                        f"Expense value for "
                        f"{category} is too large."
                    )
                }), 400

        # ----------------------------------------------------
        # GOAL
        # ----------------------------------------------------

        goal = data.get(
            "goal",
            "emergency fund"
        )

        if not isinstance(
            goal,
            str
        ):

            goal = "emergency fund"

        goal = goal.strip()

        if not goal:

            goal = "emergency fund"

        # ----------------------------------------------------
        # FINANCIAL CALCULATIONS
        # ----------------------------------------------------

        total_expenses = sum(
            expenses.values()
        )

        remaining = (
            income -
            total_expenses
        )

        planned_savings = expenses.get(
            "savings",
            0
        )

        planned_savings_percentage = (

            (planned_savings / income) * 100

            if income > 0

            else 0
        )

        remaining_percentage = (

            (remaining / income) * 100

            if income > 0

            else 0
        )

        # ----------------------------------------------------
        # BUILD PROMPT
        # ----------------------------------------------------

        prompt = build_prompt(
            income,
            expenses,
            goal
        )

        # ----------------------------------------------------
        # GENERATE AI ADVICE
        # ----------------------------------------------------

        ai_data = generate_financial_advice(
            prompt
        )

        # ----------------------------------------------------
        # RETURN RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "budget": ai_data.get(
                "budget",
                []
            ),

            "analysis": ai_data.get(
                "analysis",
                []
            ),

            "suggestions": ai_data.get(
                "suggestions",
                []
            ),

            "summary": ai_data.get(
                "summary",
                ""
            ),

            "financial_summary": {

                "income": round(
                    income,
                    2
                ),

                "total_expenses": round(
                    total_expenses,
                    2
                ),

                "remaining": round(
                    remaining,
                    2
                ),

                "remaining_percentage": round(
                    remaining_percentage,
                    2
                ),

                "planned_savings": round(
                    planned_savings,
                    2
                ),

                "planned_savings_percentage": round(
                    planned_savings_percentage,
                    2
                )
            }
        })

    except Exception as e:

        # ----------------------------------------------------
        # SERVER ERROR LOG
        # ----------------------------------------------------

        print(
            "\n" + "=" * 60
        )

        print(
            "ERROR IN /analyse"
        )

        print(
            "=" * 60
        )

        print(
            str(e)
        )

        print(
            "=" * 60 + "\n"
        )

        return jsonify({

            "success": False,

            "error": (
                "Unable to generate financial advice right now. "
                "Please try again."
            )

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "ok",

        "application":
            "Personal Finance Advisor Bot",

        "gemini_model":
            MODEL_NAME
    })


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    print(
        "\n" + "=" * 60
    )

    print(
        "PERSONAL FINANCE ADVISOR BOT"
    )

    print(
        "=" * 60
    )

    print(
        f"Gemini model: {MODEL_NAME}"
    )

    print(
        "Server: http://127.0.0.1:5000"
    )

    print(
        "=" * 60
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )