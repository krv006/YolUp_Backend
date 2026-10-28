import mimetypes

from django.http import FileResponse
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Material


def material_dict(material: Material) -> dict:
    uploader = material.uploaded_by
    return {
        'id': str(material.id), 'course_id': str(material.course_id), 'course_title': material.course.title,
        'title': material.title, 'name': material.original_name, 'size': material.size, 'kind': material.kind,
        'mime': mimetypes.guess_type(material.original_name)[0] or '',
        'url': f'/api/v1/materials/{material.id}/file/',
        'uploaded_by': {'id': str(uploader.id), 'name': uploader.get_full_name() or uploader.username} if uploader else None,
        'created_at': material.created_at,
    }


class MaterialListCreateView(generics.ListCreateAPIView):
    """`GET /materials/?course=<id>&kind=pdf|doc|audio|video|image|other&search=` va `POST` (multipart: `course`, `file`, `title`)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        params = self.request.query_params
        qs = Material.objects.filter(course__in=services.visible_courses(self.request.user)).select_related('course', 'uploaded_by')
        if params.get('course'):
            qs = qs.filter(course_id=params['course'])
        if params.get('kind'):
            qs = qs.filter(kind=params['kind'])
        if params.get('search'):
            qs = qs.filter(title__icontains=params['search'])
        return qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([material_dict(item) for item in page])

    def create(self, request, *args, **kwargs):
        material = services.upload(
            teacher=request.user, course_id=request.data.get('course'), file=request.FILES.get('file'),
            title=request.data.get('title') or '',
        )
        return Response(material_dict(material), status=status.HTTP_201_CREATED)


class MaterialDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        services.delete(user=request.user, material_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaterialFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        path, name, mime = services.file_for(user=request.user, material_id=pk)
        return FileResponse(open(path, 'rb'), as_attachment=request.query_params.get('inline') != '1', filename=name, content_type=mime)
