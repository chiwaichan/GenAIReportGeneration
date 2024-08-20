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
    # print(f"prompt= {prompt}")
    # Define the prompt for the model.
    # prompt = "Describe the purpose of a 'hello world' program in one line."

    # Format the request payload using the model's native structure.
    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "temperature": 0.0,
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
    # print(response_text)

    return response_text



def generate_chart(data, chart_title):
    """Generate a bar chart for the weighted confidence scores."""
    extracted_files = data["extracted_files"]
    processed_files = data["processed_files"]

    doc_names_extracted_files = [item['file_name'] for item in extracted_files]
    scores_extracted_files = [item['weighted_score'] for item in extracted_files]

    plt.figure(figsize=(10, 6))
    plt.bar(doc_names_extracted_files, scores_extracted_files, color='skyblue')
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

def generate_report(data, file_name):
    populate_with_values(data)

    print("outcome")
    print(json.dumps(data, indent=2))


    return
    # Create the PDF document
    processed_files = data["processed_files"]
    extracted_files = data["extracted_files"]
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
    <b>Total Tables Extracted from Source Document:</b> {len(processed_files)}<br/>
    <b>Job Status:</b> Completed<br/>
    """
    elements.append(Paragraph("Job Summary", heading_style))
    elements.append(Paragraph(job_summary, normal_style))
    elements.append(Spacer(1, 12))
    
    # Calculate weighted scores and add details for each document in processed_files
    for doc in processed_files:
        doc['weighted_score'] = 1.0
        doc_details = f"""
        <b>Document Name:</b> {doc['file_name']}<br/>
        <b>Total Fields Extracted:</b> {len(doc['fields'])}<br/>
        <b>Weighted Confidence Score:</b> {doc['weighted_score']:.2f}<br/>
        <b>Processing steps for File:</b> {'<br/>'.join(doc['processing_steps'])}<br/>

        <br/>
        <br/>
        """
        elements.append(Paragraph(f"Document: {doc['file_name']}", heading_style))
        elements.append(Paragraph(doc_details, normal_style))
        
        # Table Data
        table_data = [['Field Name', 'Extracted Value', 'Confidence Score', 'Weight', 'Notes']]  # Header
        for field in doc['fields']:
            weight = 1
            confidence_score, confidence_score_explaination = invoke_model(f"Give me a confidence score out of 1.0 for the following notes about processing a table of data, give me a response like this where the score is returned and the detailed explantion followings a '|': '0.92 | This is the explanation and so on'. If the Notes are 'None' then that is a good thing. The notes is: {''.join([note + ' ' for note in field['processing_notes']])}").split('|', 1)

            print(f"confidence_score {confidence_score}")
            table_data.append([
                        field['name'], 
                        field['value'], 
                        confidence_score, 
                        weight, 
                        ''.join([note + ' ' for note in field['processing_notes']])
                    ])

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
    
    # Calculate weighted scores for extracted_files (this was missing)
    for doc in extracted_files:
        doc['weighted_score'] = 2.0
    
    # Generate and add chart
    chart_buffer = generate_chart(data, "Weighted Confidence Scores by Document")
    chart_image = Image(chart_buffer, width=400, height=300)
    elements.append(Paragraph("Confidence Score Chart", heading_style))
    elements.append(chart_image)
    
    # Build the PDF
    pdf.build(elements)

def populate_with_values(data):
    for step in data['processing_steps']:
        print(f"Step Name: {step['step_name']}")
        
        # Loop over processing sub-steps
        for sub_step in step['processing_sub_steps']:
            print(f"  Sub Step Name: {sub_step['sub_step_name']}")
            print(f"  File Name: {sub_step['file_name']}")
            print(f"  Processing Notes: {', '.join(sub_step['processing_notes'])}")

            confidence_score_response = invoke_model(f"Give me a confidence score out of 1.0 for the following notes about processing a table of data, give me a response like this where the score is returned and the detailed explantion followings a '|': '0.92 | This is the explanation and so on'. If the Notes are 'None' then that is a good thing. The notes is: {''.join([note + ' ' for note in sub_step['processing_notes']])}").split('|', 1)

            sub_step["confidence_score"] = confidence_score = confidence_score_response[0]
            sub_step["confidence_score_explanation"] = confidence_score_explanation = confidence_score_response[1]

            # print(f"me score {confidence_score_response}")

    


data = {
    "report_context": "",
    "high_level": "",
    "processing_steps":    [
        {
            'step_name': 'process step 1',
            'weight': 1,
            'processing_notes': ['Found 3 tables.'],
            'processing_sub_steps': [
                {'sub_step_name': 'created file 1', 'file_name': 'raw/table_1.csv', 'processing_notes': ['Found 100 rows.', 
                                                                                                         'Found 90/100 rows is relevant data.', 
                                                                                                         'Deleted 3 Rows that are used for Totals.']},
                {'sub_step_name': 'created file 2', 'file_name': 'raw/table_2.csv', 'processing_notes': ['Missing Values.']},
                {'sub_step_name': 'created file 3', 'file_name': 'raw/table_3.csv', 'processing_notes': ['None.']},
            ]
        },
        {
            'step_name': 'process step 2',
            'processing_sub_steps': [
                {'sub_step_name': 'normalise file 1', 'file_name': 'normalise/table_1.csv', 'processing_notes': ['Spelling Mistakes.']},
                {'sub_step_name': 'normalise file 2', 'file_name': 'normalise/table_2.csv', 'processing_notes': ['Missing Values.']},
                {'sub_step_name': 'normalise file 3', 'file_name': 'normalise/table_3.csv', 'processing_notes': ['None.']},
            ]
        }
    ]
}


# Generate the report with charts
generate_report(data, "report_with_charts.pdf")

