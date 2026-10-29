# Archivo: src/chatbot/urls.py
from django.urls import path
from .views import ChatbotAPIView

urlpatterns = [
    # Esta es la ruta final: /api/chatbot/
    path('api/chatbot/', ChatbotAPIView.as_view(), name='chatbot_api'),
]