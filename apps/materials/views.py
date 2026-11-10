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
        'lesson_id': str(material.lesson_id) if material.lesson_id else None,
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
        if params.get('lesson'):  # `?lesson=<id>` — shu dars papkasi; `?lesson=general` — darssiz ("Umumiy") fayllar
            qs = qs.filter(lesson__isnull=True) if params['lesson'] == 'general' else qs.filter(lesson_id=params['lesson'])
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
            title=request.data.get('title') or '', lesson_id=request.data.get('lesson') or None,
        )
        return Response(material_dict(material), status=status.HTTP_201_CREATED)


class CourseFoldersView(APIView):
    """`GET /materials/courses/` — guruhlar va fayllar soni."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.course_folders(request.user))


class CourseLessonFoldersView(APIView):
    """`GET /materials/courses/<id>/lessons/` — darslar: `file_count`, `has_recording`, `has_board` (+ `general.file_count`)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        return Response(services.lesson_folders(user=request.user, course_id=course_id))


class LessonFolderView(APIView):
    """`GET /materials/lessons/<id>/` — dars papkasi: fayllar + video yozuv + doska PDF'i (havolalar bilan)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        folder = services.lesson_folder(user=request.user, lesson_id=lesson_id)
        folder['files'] = [material_dict(m) for m in folder['files']]
        return Response(folder)


class LessonBoardPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        resp = FileResponse(open(services.board_pdf_for(user=request.user, lesson_id=lesson_id), 'rb'), content_type='application/pdf')
        resp['Content-Disposition'] = 'inline; filename="doska.pdf"'
        resp['Cache-Control'] = 'no-store'
        resp['X-Content-Type-Options'] = 'nosniff'
        return resp


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
