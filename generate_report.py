from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO


import boto3
import json

from botocore.exceptions import ClientError

# Create a Bedrock Runtime client in the AWS Region of your choice.
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Set the model ID, e.g., Claude 3 Haiku.
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

def invoke_model(prompt):
    # Define the prompt for the model.
    # prompt = "Describe the purpose of a 'hello world' program in one line."

    # Format the request payload using the model's native structure.
    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    }

    # Convert the native request to JSON.
    request = json.dumps(native_request)

    try:
        # Invoke the model with the request.
        response = client.invoke_model(modelId=model_id, body=request)

    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)

    # Decode the response body.
    model_response = json.loads(response["body"].read())

    # Extract and print the response text.
    response_text = model_response["content"][0]["text"]
    print(response_text)







def calculate_weighted_score(fields, weights):
    invoke_model("Hello")
    """Calculate a weighted confidence score based on provided weights."""
    total_score = 0
    total_weight = sum(weights.values())
    for field in fields:
        weight = weights.get(field['name'], 1)  # Default weight is 1 if not specified
        total_score += field['confidence'] * weight
    return total_score / total_weight

def generate_chart(data, chart_title):
    """Generate a bar chart for the weighted confidence scores."""
    doc_names = [item['document_name'] for item in data]
    scores = [item['weighted_score'] for item in data]

    plt.figure(figsize=(10, 6))
    plt.bar(doc_names, scores, color='skyblue')
    plt.xlabel('Document Name')
    plt.ylabel('Weighted Confidence Score')
    plt.title(chart_title)
    plt.ylim(0, 1)

    # Save the chart to a BytesIO buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    return buffer

def generate_report(data, file_name, weights):
    # Create the PDF document
    pdf = SimpleDocTemplate(file_name, pagesize=A4)
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], spaceAfter=6)
    
    # Title
    title = Paragraph("Document Extraction Report", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    job_summary = f"""
    <b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
    <b>Total Documents Processed:</b> {len(data)}<br/>
    <b>Job Status:</b> Completed<br/>
    """
    elements.append(Paragraph("Job Summary", heading_style))
    elements.append(Paragraph(job_summary, normal_style))
    elements.append(Spacer(1, 12))
    
    # Calculate weighted scores and add details for each document
    for doc in data:
        doc['weighted_score'] = calculate_weighted_score(doc['fields'], weights)
        doc_details = f"""
        <b>Document Name:</b> {doc['document_name']}<br/>
        <b>Total Fields Extracted:</b> {len(doc['fields'])}<br/>
        <b>Weighted Confidence Score:</b> {doc['weighted_score']:.2f}<br/>
        <b>Errors Encountered:</b> {doc['errors']}<br/>
        """
        elements.append(Paragraph(f"Document: {doc['document_name']}", heading_style))
        elements.append(Paragraph(doc_details, normal_style))
        
        # Table Data
        table_data = [['Field Name', 'Extracted Value', 'Confidence Score', 'Weight']]  # Header
        for field in doc['fields']:
            weight = weights.get(field['name'], 1)
            table_data.append([field['name'], field['value'], f"{field['confidence']:.2f}", weight])
        
        # Create a Table
        table = Table(table_data)
        
        # Table Style
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(style)
        
        # Add the table to the elements list
        elements.append(table)
        elements.append(Spacer(1, 24))
    
    # Generate and add chart
    chart_buffer = generate_chart(data, "Weighted Confidence Scores by Document")
    chart_image = Image(chart_buffer, width=400, height=300)
    elements.append(Paragraph("Confidence Score Chart", heading_style))
    elements.append(chart_image)
    
    # Build the PDF
    pdf.build(elements)

data = {
    "report_context": "",
    "high_level": "",
    "sections":    [
        {
            'document_name': 'Invoice_001.pdf',
            'fields': [
                {'name': 'Invoice Number', 'value': 'INV-1001', 'confidence': 0.98},
                {'name': 'Date', 'value': '2024-08-10', 'confidence': 0.95},
                {'name': 'Total Amount', 'value': '$1,250.00', 'confidence': 0.96},
            ],
            'errors': 'None'
        },
        {
            'document_name': 'Invoice_002.pdf',
            'fields': [
                {'name': 'Invoice Number', 'value': 'INV-1002', 'confidence': 0.88},
                {'name': 'Date', 'value': '2024-08-12', 'confidence': 0.90},
                {'name': 'Total Amount', 'value': '$2,350.00', 'confidence': 0.89},
            ],
            'errors': 'Minor misalignment on total amount'
        }
    ]
}

# Define weights for each field
weights = {
    'Invoice Number': 2.0,
    'Date': 1.5,
    'Total Amount': 3.0
}

# Generate the report with charts
generate_report(data, "report_with_charts.pdf", weights)
