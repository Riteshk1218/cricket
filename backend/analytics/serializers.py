from rest_framework import serializers


class TrackSerializer(serializers.Serializer):
    path = serializers.CharField(max_length=200)
    visitor_id = serializers.CharField(max_length=64)
    client = serializers.ChoiceField(choices=["web", "android", "ios"], default="web")
    match = serializers.IntegerField(required=False, allow_null=True)
