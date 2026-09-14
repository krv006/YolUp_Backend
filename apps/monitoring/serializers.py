from rest_framework import serializers

from .models import ResourceSample


class ResourceSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceSample
        fields = ['id', 'cpu_percent', 'memory_percent', 'memory_used_mb', 'memory_total_mb', 'created_at']
