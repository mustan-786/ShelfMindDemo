import json
import os
import time
from datetime import date
from google import genai
from google.genai import types
import streamlit as st


# Candidate models for cascading fallback
CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]


def get_gemini_client():
    api_key = ""
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _safe_json_parse(raw_output: str):
    """Strips markdown code ticks and safely parses JSON."""
    text = raw_output.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


# =====================================================================
# GUARANTEED EXHIBITION DEMO FALLBACKS (Zero-Crash Kirana Analytics)
# =====================================================================

def _fallback_demand_engine(inventory_items: list, lang_name: str = "English"):
    """
    Deterministic rule-based Kirana Demand Radar engine.
    Runs locally with zero external API calls if the network fails.
    """
    results = []
    month = date.today().month

    # Seasonal grocery indicators for Western/Central India
    monsoon_months = [6, 7, 8, 9]
    festive_months = [8, 9, 10, 11]  # Ganesh Chaturthi, Navratri, Diwali
    summer_months = [3, 4, 5]

    for item in inventory_items:
        name = str(item.get("item_name", "")).strip()
        stock = int(item.get("current_stock", 1))
        name_lower = name.lower()

        # 1. Festive / High Velocity Staples
        if any(w in name_lower for w in ["oil", "tel", "atta", "flour", "sugar", "sakhar", "besan", "rava", "sooji", "ghee"]):
            if stock <= 8:
                status = "SURGE"
                if "mr" in lang_name.lower() or "मराठी" in lang_name:
                    reason = "सध्याच्या सणासुदीच्या हंगामामुळे दैनंदिन मागणीत मोठी वाढ."
                    action = f"स्टॉकमध्ये फक्त {stock} शिल्लक! त्वरित नवीन पुरवठा मागवा."
                elif "hi" in lang_name.lower() or "हिंदी" in lang_name:
                    reason = "त्योहारी सीजन के कारण मांग में भारी उछाल दर्ज."
                    action = f"स्टॉक में केवल {stock} यूनिट बचे हैं! तुरंत रीस्टॉक करें।"
                else:
                    reason = "High everyday staple demand surging ahead of festive season."
                    action = f"Only {stock} units left! Urgent supplier restock advised."
            else:
                status = "STABLE"
                if "mr" in lang_name.lower() or "मराठी" in lang_name:
                    reason = "नियमित किराणा खप, स्थिर पुरवठा."
                    action = "सध्याचा स्टॉक योग्य पातळीवर आहे."
                elif "hi" in lang_name.lower() or "हिंदी" in lang_name:
                    reason = "दैनिक किराना बिक्री, संतुलित प्रवाह."
                    action = "स्टॉक पर्याप्त स्तर पर है।"
                else:
                    reason = "Regular household staple with consistent turnover."
                    action = "Stock levels optimal for current sales velocity."

        # 2. Tea, Biscuits & Snacks
        elif any(w in name_lower for w in ["tea", "chai", "patti", "maggi", "noodle", "biscuit", "parle", "toast"]):
            status = "SURGE" if stock < 5 else "STABLE"
            if "mr" in lang_name.lower() or "मराठी" in lang_name:
                reason = "दैनिक चहा-नाश्ता खपाची उच्च गती."
                action = "काऊंटर जवळ दर्शनी भागात ठेवा."
            elif "hi" in lang_name.lower() or "हिंदी" in lang_name:
                reason = "शाम के नाश्ते और चाय के समय में तेज खपत."
                action = "दुकान के फ्रंट शेल्फ पर प्रदर्शित करें।"
            else:
                reason = "High impulse grocery velocity for morning and evening routines."
                action = "Maintain front display for fast walk-in turnover."

        # 3. Summer items vs Monsoon
        elif any(w in name_lower for w in ["cold drink", "sharbat", "glucose", "ice"]):
            if month in summer_months:
                status = "SURGE"
                reason = "Seasonal hot weather surge."
                action = "Keep chilled units ready."
            else:
                status = "DEAD_STOCK"
                reason = "Off-season weather, consumer purchase dropped."
                action = "Clear existing batch; do not reorder now."

        # 4. Low stock general catch-all
        elif stock <= 2:
            status = "SURGE"
            reason = "Critical shelf depletion threshold reached."
            action = "Reorder from wholesaler before stockout."

        # 5. High volume slow mover
        elif stock >= 25:
            status = "DEAD_STOCK"
            if "mr" in lang_name.lower() or "मराठी" in lang_name:
                reason = "भांडवल अडकले आहे, अपेक्षित वेगाने खप नाही."
                action = "कॉम्बो ऑफर देऊन स्टॉक मोकळा करा."
            elif "hi" in lang_name.lower() or "हिंदी" in lang_name:
                reason = "पूंजी फंसी हुई है, बिक्री की गति धीमी है।"
                action = "कॉम्बो छूट देकर निकासी तेज करें।"
            else:
                reason = "Capital tied up; movement velocity slower than normal."
                action = "Create combo clearance offer near cash counter."
        else:
            status = "STABLE"
            reason = "Steady turnover rate in local Kirana pattern."
            action = "Standard weekly replenishment recommended."

        results.append({
            "item_name": name,
            "status": status,
            "reason": reason,
            "action": action
        })

    return results


def _fallback_dead_stock_tactics(dead_items: list, lang_name: str = "English"):
    strategies = []
    for item in dead_items:
        name = str(item.get("item_name", "Product"))
        if "mr" in lang_name.lower() or "मराठी" in lang_name:
            strategies.append({
                "item_name": name,
                "tactic": "काऊंटर कॉम्बो स्कीम",
                "pitch": f"काकू, या {name} सोबत चहा पावडर घेतल्यास ₹10 थेट सूट मिळेल!",
                "discount_recommendation": "₹10 Combo Off"
            })
        elif "hi" in lang_name.lower() or "हिंदी" in lang_name:
            strategies.append({
                "item_name": name,
                "tactic": "काउंटर कॉम्बो बंडल",
                "pitch": f"भैया, आज {name} के साथ 1 किलो चीनी लेने पर विशेष ₹10 की छूट है!",
                "discount_recommendation": "₹10 Combo Off"
            })
        else:
            strategies.append({
                "item_name": name,
                "tactic": "Counter Bundle Scheme",
                "pitch": f"Special combo: Buy {name} with tea/atta and get an instant ₹10 rebate!",
                "discount_recommendation": "5% Clearance Off"
            })
    return strategies


# =====================================================================
# CORE API FUNCTIONS WITH AUTOMATIC FAILOVER
# =====================================================================

def analyze_inventory_demand(
    inventory_items: list,
    location: str = "Maharashtra, India",
    lang_name: str = "English",
):
    """Evaluates regional demand signals, seasonal spikes, and stock health."""
    if not inventory_items:
        return [], None

    client = get_gemini_client()
    if not client:
        return _fallback_demand_engine(inventory_items, lang_name), None

    current_date = date.today().strftime("%B %d, %Y")
    prompt = f"""
    You are an expert FMCG & Kirana Store supply chain analyst in {location}.
    Current Date: {current_date}
    Target Language for descriptions: {lang_name}
    
    Analyze the following shopkeeper inventory:
    {json.dumps(inventory_items, indent=2)}
    
    Evaluate each item based on:
    1. Seasonal Demand: Current month/season in {location} (monsoon, summer, winter, harvest).
    2. Upcoming Festivals & Events in the next 30-45 days.
    3. Stock Status:
       - 'SURGE': High upcoming demand or dangerously low stock.
       - 'STABLE': Regular demand.
       - 'DEAD_STOCK': Low turnover risk or overstock.

    Write the 'reason' and 'action' fields strictly in {lang_name}.
    Keep 'status' as one of the exact English enum values: "SURGE", "STABLE", "DEAD_STOCK".

    Respond STRICTLY with a valid JSON array of objects:
    [
      {{
        "item_name": "string",
        "status": "SURGE" | "STABLE" | "DEAD_STOCK",
        "reason": "Short 1-line reason in {lang_name}",
        "action": "Actionable 1-line restocking or discount advice in {lang_name}"
      }}
    ]
    """

    for model_name in CANDIDATE_MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                if response and response.text:
                    parsed = _safe_json_parse(response.text)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        return parsed, None
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "spike" in err_str.lower():
                    time.sleep(1)
                    continue
                break

    # If all models hit quotas or capacity spikes, serve the deterministic rule-based output
    return _fallback_demand_engine(inventory_items, lang_name), None


def audit_shelf_photo_with_ai(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    lang_name: str = "English",
):
    """Analyzes a Kirana shelf photograph to recognize products and evaluate movement."""
    client = get_gemini_client()
    if not client:
        return [], "Gemini API client not initialized."

    prompt = f"""
    You are an automated Kirana Store Shelf Inspector in India.
    Inspect this photograph of grocery shelves/racks.
    Language for observations: {lang_name}

    Tasks:
    1. Identify distinct FMCG/grocery packaged items visible on the shelves (e.g., biscuits, tea, soaps, detergents, cooking oil, spices, noodles).
    2. Estimate the visible front-facing packet or bottle count.
    3. Note shelf placement observation (e.g., 'Primary eye-level display', 'Stagnant rear shelf', 'Single leftover unit').

    Return STRICTLY a JSON array of objects:
    [
      {{
        "item_name": "Recognized Product Name",
        "estimated_count": 5,
        "shelf_observation": "Brief observation in {lang_name}"
      }}
    ]
    """

    for model_name in CANDIDATE_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            if response and response.text:
                return _safe_json_parse(response.text), None
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "404" in err_str:
                continue
            return [], str(e)

    return [], "Model currently unavailable. Please snap again."


def generate_dead_stock_strategy(dead_items: list, lang_name: str = "English"):
    """Generates Kirana combo clearance ideas and customer counter pitches."""
    if not dead_items:
        return []

    client = get_gemini_client()
    if not client:
        return _fallback_dead_stock_tactics(dead_items, lang_name)

    prompt = f"""
    You are a Kirana store retail consultant in Maharashtra, India.
    Language: {lang_name}

    These grocery products have had no sales movement and are blocking shop capital:
    {json.dumps(dead_items, indent=2)}

    For each product, generate a retail clearance tactic tailored to an Indian Kirana store:
    - Counter bundle offer (e.g., Pair with tea powder or atta)
    - Direct counter discount
    - Verbal sales pitch for the shopkeeper to use with walk-in customers

    Return STRICTLY a JSON array of objects:
    [
      {{
        "item_name": "string",
        "tactic": "Short strategy tag in {lang_name}",
        "pitch": "Counter sales pitch in {lang_name}",
        "discount_recommendation": "e.g., ₹5 Off or Combo Scheme in {lang_name}"
      }}
    ]
    """

    for model_name in CANDIDATE_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            if response and response.text:
                return _safe_json_parse(response.text)
        except Exception:
            continue

    return _fallback_dead_stock_tactics(dead_items, lang_name)
