from django.shortcuts import render
from condo_payments.serializer import CondoPaymentSerializer
from rest_framework.viewsets import ModelViewSet
from condo_payments.models import CondoPaymentModel
from condo_payments.permissions import IsAdminOrReadyOnlyForAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

class CondoPaymentViewSet(ModelViewSet):
    serializer_class = CondoPaymentSerializer
    permission_classes = [IsAdminOrReadyOnlyForAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return CondoPaymentModel.objects.all().order_by('-created_at')
        return CondoPaymentModel.objects.filter(payer_user = self.request.user)
    
    @action(
        methods=['patch'],
        detail=False,
        url_name='set_paid_status/'
    )
    def set_paid_status(self, request, *args, **kwargs):
        # Get the list of all id the staff want to put paid
        paid_payment_ids = request.data.get('paid_payment_ids')
        
        # Check if the type of the data passed to us (need to be a list)
        if type(paid_payment_ids) != type([]) or len(paid_payment_ids) <= 0:
            raise ValidationError({'Invalid JSON': 'The IDs list is invalid or empty'})
        
        payments = []
        incorrect_ids = []
        for id in paid_payment_ids:
            payment = CondoPaymentModel.objects.filter(id = id)
            if payment:
                if payment[0].status != 'paid':
                    payments.append(payment)
                else:
                    incorrect_ids.append(id)
            else:
                incorrect_ids.append(id)
        
        if incorrect_ids:
            raise ValidationError({'These IDs are invalid or already paid': incorrect_ids})

        for payment in payments:
            payment[0].status = 'paid'
            payment[0].save()
        
        return Response(status=status.HTTP_200_OK)
    