import csv
from io import StringIO
from rest_framework.renderers import BaseRenderer

class CSVRenderer(BaseRenderer):
    media_type = 'text/csv'
    format = 'csv'

    def render(self, data, media_type=None, renderer_context=None):
        if data is None:
            return ""

        if isinstance(data, dict) and "data" in data and "message" in data:
            data = data["data"]

        # Handle both list of dicts and single dict
        if not isinstance(data, list):
            data = [data]

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        # Set filename for browser download
        response = renderer_context.get('response')
        if response:
            response['Content-Disposition'] = 'attachment; filename="report.csv"'
            
        return output.getvalue()