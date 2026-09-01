from django.db import models
from django.contrib.auth.models import User
from orders.models import Order 


class Conversations(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE , related_name= "conversations" )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name= "conversations")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation #{self.id} - {self.user.username}"
    
class Message(models.Model):
    ROLE_CHOICES = [
        ("user" , "User"),
        ("agent","Agent"),

    ]
    conversation = models.ForeignKey(Conversations, on_delete=models.CASCADE, related_name= "message" )
    role = models.CharField(max_length=20, choices = ROLE_CHOICES)
    content= models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__ (self):
        return f"{self.role}: {self.content[:50]}" #Agent : we are checking your request


class AgentLog(models.Model):
    EVENT_CHOICES = [
        ("support", "Support Agent"),
        ("tool_call", "Tool Call"),
        ("tool_result", "Tool Result"),
        ("manager", "Manager Agent"),
        ("risk", "Risk Agent"),
        ("final", "Final Reply"),
    ]
    conversation = models.ForeignKey(Conversations, on_delete=models.CASCADE, related_name="agentlogs")
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__ (self):
        return f"[{self.event_type}] - {self.message[:40]}" 