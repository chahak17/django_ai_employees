from django.shortcuts import render, get_object_or_404
import json 
from django.http import JsonResponse
import time
from .models import Conversations, Message
from orders.models import Order 
from support.agent import run_support_agent



def chat(request, order_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get("message")


        if not user_message:
          return JsonResponse({"error": "Empty message"} , status = 400)
    
        order= get_object_or_404(Order , id=order_id, user= request.user)


        conversation ,created_at  = Conversations.objects.get_or_create(user=request.user , order=order)

        Message.objects.create(conversation= conversation , role ="user", content= user_message)

        # send user msg and convo to LLM
        reply = run_support_agent (user_message, conversation.id, order.id, request.user.id)

        # Store the LLm reply 
        Message.objects.create(conversation= conversation , role ="assistant", content= reply)
    
        # time.sleep(4)
        return JsonResponse({"reply": reply })   
 