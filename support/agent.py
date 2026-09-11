#the brain , from  where the agent thinks
from anthropic import Anthropic
from django.conf import settings
from .tools import get_order_details, get_refund_history, check_delivery_status, get_customer_risk_profile
from .models import Conversations,Message, AgentLog
# Intialize the anthropic client
client = Anthropic(
    api_key=settings.ANTHROPIC_API_KEY)


anthropic_model=settings.ANTHROPIC_MODEL

# SUPPORT SSYTEM PROMPT ->> MAYA'S JOB DESC
SUPPORT_SYSTEM_PROMPT = """
You are Maya, a customer support agent at CoolBreeze AC.
You help customers with issues related to their AC orders.

Your responsibilities:
- Always use your tools to gather facts before responding
- Check order details when customer mentions their order
- Check refund history before making any refund decisions
- Be empathetic but honest

Your personality:
- Friendly and professional
- Patient even when customer is angry
- Clear and concise in your replies
- tell a joke if they ask.

Important rules:
- Always check order details first before responding
- Never approve or deny a refund yourself
- If the customer requests a refund or asks for a refund update, you MUST use the necessary tools and escalate the case to the manager before responding.
- Do not tell the customer that a case has been escalated unless you actually called escalate_to_manager in the current turn or have a stored escalation result.
- If the manager returns a final decision, communicate that decision clearly to the customer.
- No emojis should be used
 
"""


MANAGER_SYSTEM_PROMPT = """ 
Your are a senior support manager at CoolBreeze AC .
A support agent has escalated a customer case to you for a refund decisions

Your Responsibilities:
- Review the case summary carefully
- Consider the cuatomer's refund history
- Make a fair and final refund decision
- Give a clear readon for your decision

Your decision options:
- Approve refund - if the case is genuine and within policy
- Deny refund - if the case is supicious or outside policy
- Escalate to risk team - if you suspect fraud

Important rules:
- Be fair but firm
- Base decision on facts - not emotions
- Always give a specific reason for your decision
- Keep your resaons concise and professional
- No emojies

"""
RISK_SYSTEM_PROMPT = """
You are fraud risk analyst at CoolBreeze AC.
A support manager has sent you a customer profile for risk assessment. 

Your Job:
- Analyse the customer's order and refund patterns
- Identify suspicious behaviour
- Return a clear risk verdict

Risk Levels:
- LOW - genuine customer, normal behaviour
- MEDIUM - some suspicious behaviour
- HIGH - clear fraud pattern , recommend denail

Your response format:
- Risk levels : LOW, MEDIUM , HIGH
- Key Signals : what you found suspicious or genuine
- Recommendation : what manager should do

Important:
- Be objective : base verdict on data only
- One bad refund does not make someone fraud
- Look for patterns - not isolated incidents
"""

# SUPPORT TOOLS ->> Tool schemas, that  ai agents will read
SUPPORT_TOOLS = [
    {
        "name": "get_order_details",
        "description": "fetch complte order details including status, carrier , tracking number and days since the order was placed . use this when cuatomer mentions their complain about delivery",
        "input_schema": {
            "type": "object",
            "properties":{
                "order_id": {
                   "type":  "integer",
                   "description": "The order ID to look up"
                } 
            },
            "required": ["order_id"]
        }
    },


    {
    "name": "get_refund_history",
    "description": "Get complete refund history for a user. Use this before making any refund related decisions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "The user ID to check refund history for"
            }
        },
        "required": ["user_id"]
    }
    },

   {
    "name": "check_delivery_status",
    "description": "Check current delivery status using tracking number and carrier. Use this when customer complains about delayed or missing delivery.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tracking_number": {
                "type": "string",
                "description": "The shipment tracking number"
            },
            "carrier": {
                "type": "string",
                "description": "The carrier name for example BlueDart or Delhivery"
            }
        },
        "required": ["tracking_number", "carrier"]
    }
}, 

{
    "name" : "escalate_to_manager",
    "description": "Esacalte the case to the manager for refund decision. Use thus when customer requests a refund or compensation. Preapre a detalied case summary including order details , refund history, and customer complaint before escalating.",
    "input_schema": {
        "type": "object",
        "properties": {
            "case_summary": {
                "type": "string",
                "description": "Complete case summary including the order details , refund history and customer complaint"
            }
        },
        "required": ["case_summary"]
    }
}

]

MANAGER_TOOLS = [
    {
            "name": "assess_fraud_risk",
            "description": "Consult the risk agent to assess fraud risk for a customer . Use this when refund request looks suspicious or cuatomer has multiple refund requests. Pass the user_id to get a risk verdict",
            "input_schema": {
                "type": "object",
                "properties":{
                    "user_id": {
                       "type":  "integer",
                       "description": "The user ID is to assess fraud risk for"
                    } 
                },
                "required": ["user_id"]
            }
        },
]

RISK_TOOLS = [
    {
            "name": "get_customer_risk_profile",
            "description": "Get complete risk profile for customer including order history , refund patterns and ratio . use this to assess fraud risk ",
            "input_schema": {
                "type": "object",
                "properties":{
                    "user_id": {
                       "type":  "integer",
                       "description": "The user ID to assess risk for"
                    } 
                },
                "required": ["user_id"]
            }
        },
]


# EXECUTE-TOOL() ->> Bridge between claude and python function(tools)
def execute_tool(tool_name, tool_input):
    if tool_name == "get_order_details":
       return get_order_details(tool_input["order_id"])

    if tool_name == "get_refund_history":
        return get_refund_history(tool_input["user_id"])

    if tool_name == "check_delivery_status":
        return check_delivery_status(tool_input["tracking_number"], tool_input["carrier"])

    if tool_name ==  "escalate_to_manager":
        case_summary = tool_input["case_summary"]
        print("escalating to manager ==>", case_summary)
        decision =  run_manager_agent(case_summary)
        print("decision ==>", decision)
        return decision

    if tool_name == 'assess_fraud_risk':
        user_id = tool_input['user_id']
        print("Consulting risk agent for users==>", user_id )
        verdict = run_risk_agent(user_id)
        print("risk verdict==>", verdict)
        return verdict


    if tool_name == 'get_customer_risk_profile':
        return get_customer_risk_profile(tool_input['user_id'])
    
    


    
# AGENT LOOP ->> While loop that loops until the task is done!
def run_support_agent(user_message, conversation_id, order_id, user_id):
    conv = Conversations.objects.get(id=conversation_id)

    conversation_messages = []

    for msg in conv.message.order_by("created_at"):
        conversation_messages.append({
            "role": msg.role,
            "content": msg.content
        })

    while True:

        # Send this conversation to Claude
        response = client.messages.create(
            model=anthropic_model,
            max_tokens=1024,
            system=SUPPORT_SYSTEM_PROMPT + f"\n\nContext: this conversation is about Order #{order_id}, user: {user_id}",
            tools=SUPPORT_TOOLS,
            messages=conversation_messages
        )

        

        # -------------------------------------------------
        # CLAUDE WANTS TO USE A TOOL
        # -------------------------------------------------
        if response.stop_reason == "tool_use":

            # VERY IMPORTANT:
            # First add Claude's tool_use response
            # to the conversation.
            conversation_messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []

            for block in response.content:

                if block.type == "tool_use":

                    print("tool call ==>", block.name)
                    print("tool input ==>", block.input)

                    # Execute the Python tool
                    result = execute_tool(block.name, block.input)
                    print('executing_tool==>',block.name)
                    print('block.input==>', block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })

            # Send the tool result back to Claude
            conversation_messages.append({
                "role": "user",
                "content": tool_results
            })

            # Continue the while loop.
            # Claude will now see the tool result.
            continue

        # -------------------------------------------------
        # CLAUDE IS DONE
        # -------------------------------------------------
        else:
            for block in response.content:
              if block.type == "text":
                return block.text

        return "Sorry, I couldn't generate a response."


def run_manager_agent(case_summary):
    manager_messages= [
        {"role": "user", "content": case_summary} # user is task giver hence maya is user here
    ]

    while True:
        response = client.messages.create(
            model = anthropic_model,
            max_tokens = 1024,
            system = MANAGER_SYSTEM_PROMPT,
            tools = MANAGER_TOOLS,
            messages = manager_messages
        )

        if response.stop_reason == 'tool_use':
            tool_result = []
            for block in response.content:
                if block.type == 'tool_use':
                    result = execute_tool(block.name, block.input)


                    tool_result.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })

            manager_messages.append({
                "role": "assistant",
                "content": response.content 
            })


            manager_messages.append({
                "role": "user",
                "content": tool_result 
            })
            continue
        else:
           for block in response.content:
              if block.type == "text":
                return block.text

        return "Manager agent returned no text response."



def run_risk_agent(user_id):
    risk_messages = [
        {
            "role": "user",
            "content": f"Please assess the fraud risk for user ID {user_id}. Use your tool to get their profile and return a verdict."

        }
    ]

    while True :
        response = client.messages.create(
            model = anthropic_model,
            max_tokens = 1024,
            system = RISK_SYSTEM_PROMPT,
            tools = RISK_TOOLS,
            messages = risk_messages
        )


        print("risk stop_reason==>", response.stop_reason)

        if response.stop_reason == 'tool_use':
            tool_result = []
            for block in response.content:
               if block.type == 'tool_use':
                   print("risk tool call==>", block.name)
                   print("risk tool input==>", block.input)


                   result = execute_tool(block.name, block.input)
                   print("risk tool result==>", result)


                   tool_result.append({
                       "type": "tool_result",
                       "tool_use_id": block.id,
                       "content": str(result)
                   })


            risk_messages.append({
                "role": "assistant",
                "content": response.content
            })  

            risk_messages.append({
                "role": "user",
                "content": tool_result
            })

            continue


        else:
            for block in response.content:
              if block.type == "text":
               return block.text
            
        return "risk agent returned no text response."





    


