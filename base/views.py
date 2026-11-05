from django.shortcuts import render, get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from base import permissions

class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

class ActiveViewSet(BaseViewSet):
    """ Define queryset with manager all_objects so the actions from this view can interact with inactive objects."""

    def get_queryset(self):
        if self.action in ['all', 'inactive', 'reactivate']:
            return super().get_queryset()
        return super().get_queryset().filter(is_active=True)

    def destroy(self, request, *args, **kwargs):
        """ Updates the object to inactive """
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['GET'])
    def all(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def inactive(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().filter(is_active=False))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['PUT'])
    def reactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_active:
            Response(status=status.HTTP_204_NO_CONTENT)
        instance.is_active = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)