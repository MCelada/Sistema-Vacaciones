from django.http import HttpResponse
from django.template.loader import render_to_string
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import LeaveRequest
from weasyprint import HTML

class LeaveRequestPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            req = LeaveRequest.objects.select_related('employee').get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return HttpResponse('Not found', status=404)
        html_string = render_to_string('leave/request_pdf.html', {'request': req})
        pdf_file = HTML(string=html_string).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="leave_request_{pk}.pdf"'
        return response
