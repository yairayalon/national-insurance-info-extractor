import streamlit as st
import json
import tempfile
from pathlib import Path
import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import FormProcessor

# Page configuration
st.set_page_config(
    page_title="Israeli National Insurance Form Processor",
    page_icon="📋",
    layout="wide"
)


# Initialize processor
@st.cache_resource
def get_processor():
    return FormProcessor()


def main():
    st.title("Israeli National Insurance Form Processor")
    st.markdown("### Extract structured data from ביטוח לאומי forms")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Settings")
        show_validation = st.checkbox("Show Validation Results", value=True)
        show_raw = st.checkbox("Show Raw JSON", value=True)

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Upload Form")
        uploaded_file = st.file_uploader(
            "Choose a PDF or image file",
            type=['pdf', 'jpg', 'jpeg', 'png'],
            help="Upload a filled National Insurance form"
        )

        if uploaded_file is not None:
            # Display file info
            st.success(f"File uploaded: {uploaded_file.name}")
            st.info(f"Size: {uploaded_file.size / 1024:.2f} KB")

            # Process button
            if st.button("Process Form", type="primary"):
                with st.spinner("Processing form... This may take a moment."):
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(
                            uploaded_file.name).suffix) as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name

                    # Process the form
                    processor = get_processor()
                    result = processor.process_form(tmp_path)

                    # Store result in session state
                    st.session_state['result'] = result

                    # Clean up temp file
                    Path(tmp_path).unlink()

    with col2:
        st.header("Extracted Data")

        if 'result' in st.session_state:
            result = st.session_state['result']

            if result['status'] == 'success':
                # Validation results
                if show_validation:
                    st.subheader("Validation Results")

                    # Display scores
                    col1, col2 = st.columns(2)
                    with col1:
                        completeness = result['validation'].get('completeness_score', 0)
                        st.metric("Completeness", f"{completeness:.1f}%")

                        # Show empty fields
                        empty_fields = result['validation'].get('empty_fields', [])
                        if empty_fields:
                            with st.expander(f"Empty Fields ({len(empty_fields)})"):
                                for field in empty_fields:
                                    st.write(f"• {field}")
                        else:
                            st.success("All fields completed!")

                    with col2:
                        accuracy = result['validation'].get('accuracy_score', 0)
                        st.metric("OCR Confidence", f"{accuracy:.1f}%")

                    # Display warnings
                    if result['validation']['warnings']:
                        st.warning("Validation Warnings")
                        for warning in result['validation']['warnings']:
                            st.write(f"• {warning}")

                # Display extracted data in organized tabs
                st.subheader("Extracted Data")
                tabs = st.tabs(["Personal Info", "Address", "Injury Details", "Medical Info"])

                with tabs[0]:
                    st.subheader("Personal Information")
                    data = result['data']

                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Last Name", value=data.get('lastName', ''), disabled=True)
                        st.text_input("First Name", value=data.get('firstName', ''), disabled=True)
                        st.text_input("ID Number", value=data.get('idNumber', ''), disabled=True)
                    with col2:
                        st.text_input("Gender", value=data.get('gender', ''), disabled=True)
                        dob = data.get('dateOfBirth', {})
                        st.text_input("Date of Birth",
                                      value=f"{dob.get('day', '')}/{dob.get('month', '')}/{dob.get('year', '')}",
                                      disabled=True)

                    st.text_input("Landline Phone", value=data.get('landlinePhone', ''), disabled=True)
                    st.text_input("Mobile Phone", value=data.get('mobilePhone', ''), disabled=True)

                with tabs[1]:
                    st.subheader("Address Information")
                    addr = data.get('address', {})

                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Street", value=addr.get('street', ''), disabled=True)
                        st.text_input("House Number", value=addr.get('houseNumber', ''), disabled=True)
                        st.text_input("Entrance", value=addr.get('entrance', ''), disabled=True)
                    with col2:
                        st.text_input("Apartment", value=addr.get('apartment', ''), disabled=True)
                        st.text_input("City", value=addr.get('city', ''), disabled=True)
                        st.text_input("Postal Code", value=addr.get('postalCode', ''), disabled=True)

                with tabs[2]:
                    st.subheader("Injury Information")

                    injury_date = data.get('dateOfInjury', {})
                    st.text_input("Date of Injury",
                                  value=f"{injury_date.get('day', '')}/{injury_date.get('month', '')}/{injury_date.get('year', '')}",
                                  disabled=True)
                    st.text_input("Time of Injury", value=data.get('timeOfInjury', ''), disabled=True)
                    st.text_input("Job Type", value=data.get('jobType', ''), disabled=True)
                    st.text_input("Accident Location", value=data.get('accidentLocation', ''), disabled=True)
                    st.text_input("Accident Address", value=data.get('accidentAddress', ''), disabled=True)
                    st.text_area("Accident Description", value=data.get('accidentDescription', ''), disabled=True, height=100)
                    st.text_input("Injured Body Part", value=data.get('injuredBodyPart', ''), disabled=True)

                with tabs[3]:
                    st.subheader("Medical Institution Fields")
                    med = data.get('medicalInstitutionFields', {})

                    st.text_input("Health Fund Member", value=med.get('healthFundMember', ''), disabled=True)
                    st.text_input("Nature of Accident", value=med.get('natureOfAccident', ''), disabled=True)
                    st.text_area("Medical Diagnoses", value=med.get('medicalDiagnoses', ''), disabled=True, height=100)

                # Raw JSON display
                if show_raw:
                    st.subheader("Raw JSON Output")
                    st.json(result['data'])

                # Download button
                json_str = json.dumps(result['data'], ensure_ascii=False, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name="extracted_data.json",
                    mime="application/json"
                )

            else:
                st.error(f"Processing failed: {result.get('error', 'Unknown error')}")
        else:
            st.info("Upload and process a form to see extracted data here")


if __name__ == "__main__":
    main()