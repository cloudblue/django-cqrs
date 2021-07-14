from rest_framework import serializers
from app.models import Purchase


class UserActionSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    action_type = serializers.CharField(default='purchase')
    action_time = serializers.DateTimeField(source='buy_time')

    def get_id(self, obj):
        return f'purchase_{obj.pk}'

    class Meta:
        model = Purchase
        fields = ('id', 'user_id', 'action_type', 'action_time')
