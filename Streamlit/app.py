import streamlit as st
import requests
import pandas as pd
from typing import Optional, Dict, Any


st.set_page_config(
    page_title="NFRA Compliance Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #1E3A5F;
        --success-color: #28a745;
        --danger-color: #dc3545;
        --warning-color: #ffc107;
        --info-color: #17a2b8;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1E3A5F 0%, #2E5077 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Scorecard styling */
    .scorecard {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 4px solid #1E3A5F;
    }
    
    .scorecard-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
    }
    
    .scorecard-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .grade-a { color: #28a745 !important; }
    .grade-b { color: #17a2b8 !important; }
    .grade-c { color: #ffc107 !important; }
    .grade-d, .grade-f { color: #dc3545 !important; }
    
    .status-compliant {
        color: #28a745 !important;
    }
    
    .status-non-compliant {
        color: #dc3545 !important;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: #f8f9fa;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1E3A5F;
        color: white;
    }
    
    /* Alert cards */
    .risk-high {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    
    .risk-medium {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    
    .risk-low {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    
    /* Summary card */
    .summary-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 3px solid #1E3A5F;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# API Integration
# =============================================================================
API_BASE_URL = "http://localhost:8001"


def validate_report(uploaded_file) -> Dict[str, Any]:
    """Send PDF to API for validation and return response."""
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
        response = requests.post(
            f"{API_BASE_URL}/validate_report",
            files=files,
            timeout=300  # 5 minute timeout for large reports
        )
        response.raise_for_status()
        json_data = response.json()
        
        # Validate response is not empty
        if not json_data:
            return {"success": False, "error": "API returned empty response."}
        
        return {"success": True, "data": json_data}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Connection refused. Please ensure the API server is running on localhost:8000"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out. The report may be too large or the server is busy."}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"API Error: {e.response.status_code} - {e.response.text}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def render_header(metadata: Dict[str, Any]):
    """Render the main header with company information."""
    company_name = metadata.get("company_name", "Unknown Company")
    cin = metadata.get("cin", "N/A")
    fy = metadata.get("fy", "N/A")
    report_type = metadata.get("report_type", "Financial Report")
    
    st.markdown(f"""
    <div class="main-header">
        <h1>📊 {company_name}</h1>
        <p><strong>CIN:</strong> {cin} | <strong>Financial Year:</strong> {fy} | <strong>Type:</strong> {report_type}</p>
    </div>
    """, unsafe_allow_html=True)


def render_assessment_scorecard(data: Dict[str, Any]):
    # Safely extract assessment data
    assessment = data.get("assessment", {})
    
    overall_score = assessment.get("overall_score", "N/A")
    grade = assessment.get("grade", "N/A")
    status = assessment.get("status", "N/A")
    
    col1, col2, col3 = st.columns(3)
    
    # Metric 1: Overall Score
    with col1:
        if isinstance(overall_score, (int, float)):
            score_display = f"{overall_score}/100"
            progress_value = overall_score / 100
        else:
            score_display = str(overall_score)
            progress_value = 0
        
        st.markdown(f"""
        <div class="scorecard">
            <div class="scorecard-label">Overall Score</div>
            <div class="scorecard-value">{score_display}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if isinstance(overall_score, (int, float)):
            st.progress(progress_value)
    
    # Metric 2: Grade (Color-coded)
    with col2:
        grade_upper = str(grade).upper() if grade else "N/A"
        
        # Determine grade color class
        if grade_upper.startswith("A"):
            grade_class = "grade-a"
            grade_emoji = "🏆"
        elif grade_upper.startswith("B"):
            grade_class = "grade-b"
            grade_emoji = "👍"
        elif grade_upper.startswith("C"):
            grade_class = "grade-c"
            grade_emoji = "⚠️"
        elif grade_upper.startswith("D") or grade_upper.startswith("F"):
            grade_class = "grade-d"
            grade_emoji = "❌"
        else:
            grade_class = ""
            grade_emoji = "📊"
        
        st.markdown(f"""
        <div class="scorecard">
            <div class="scorecard-label">Grade</div>
            <div class="scorecard-value {grade_class}">{grade_emoji} {grade}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Metric 3: Status
    with col3:
        status_upper = str(status).upper() if status else "N/A"
        
        if status_upper in ["COMPLIANT", "PASS", "PASSED"]:
            status_class = "status-compliant"
            status_emoji = "✅"
        elif status_upper in ["NON_COMPLIANT", "NON-COMPLIANT", "FAIL", "FAILED"]:
            status_class = "status-non-compliant"
            status_emoji = "❌"
        else:
            status_class = ""
            status_emoji = "ℹ️"
        
        st.markdown(f"""
        <div class="scorecard">
            <div class="scorecard-label">Status</div>
            <div class="scorecard-value {status_class}">{status_emoji} {status}</div>
        </div>
        """, unsafe_allow_html=True)


def render_executive_summary(data: Dict[str, Any]):
    """Render the Executive Summary tab."""
    summary = data.get("summary", None)
    risk_analysis = data.get("risk_analysis", {})
    
    st.subheader("📋 Summary Details")
    
    # Check if summary exists
    if summary is None:
        st.warning("⚠️ Summary data is not available for this report.")
    elif not isinstance(summary, dict):
        st.warning("⚠️ Summary data is in an unexpected format.")
    else:
        # Summary details as styled bullet points
        details = summary.get("details", [])
        if details and isinstance(details, list):
            for detail in details:
                if isinstance(detail, str):
                    st.info(f"📌 {detail}")
                elif isinstance(detail, dict):
                    # Handle dict-format details
                    detail_text = detail.get("text", detail.get("message", str(detail)))
                    st.info(f"📌 {detail_text}")
        else:
            st.info("No specific details available in the summary.")
        
        # Show critical issues count if available
        critical_issues = summary.get("critical_issues", 0)
        if critical_issues and critical_issues > 0:
            st.error(f"🚨 **Critical Issues Found:** {critical_issues}")
    
    st.markdown("---")
    
    # Risk Analysis Alerts
    st.subheader("⚠️ Risk Analysis")
    
    if not risk_analysis:
        st.success("✅ No risk analysis data available.")
        return
    
    risks = risk_analysis.get("risks", [])
    if risks:
        for risk in risks:
            level = risk.get("level", "low").lower()
            description = risk.get("description", "")
            category = risk.get("category", "General")
            
            if level == "high":
                st.error(f"🔴 **HIGH RISK - {category}:** {description}")
            elif level == "medium":
                st.warning(f"🟡 **MEDIUM RISK - {category}:** {description}")
            else:
                st.info(f"🔵 **LOW RISK - {category}:** {description}")
    else:
        # Check for legacy format
        high_risks = risk_analysis.get("high", [])
        medium_risks = risk_analysis.get("medium", [])
        low_risks = risk_analysis.get("low", [])
        
        if high_risks:
            for risk in high_risks:
                st.error(f"🔴 **HIGH RISK:** {risk}")
        if medium_risks:
            for risk in medium_risks:
                st.warning(f"🟡 **MEDIUM RISK:** {risk}")
        if low_risks:
            for risk in low_risks:
                st.info(f"🔵 **LOW RISK:** {risk}")
        
        if not (high_risks or medium_risks or low_risks):
            st.success("✅ No significant risks identified.")


def render_compliance_audit(data: Dict[str, Any]):
    """Render the Compliance Audit tab with styled dataframe."""
    validation_details = data.get("validation_details", {})
    compliance_checks = validation_details.get("compliance_checks", {})
    checks = compliance_checks.get("details", [])
    
    st.subheader("📑 Compliance Check Results")
    
    if not checks:
        st.info("No compliance checks available.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(checks)
    
    # Ensure required columns exist
    expected_cols = ["rule_id", "description", "status", "evidence", "reasoning"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = "N/A"
    
    # Rename columns for display
    df = df.rename(columns={
        "rule_id": "Rule ID",
        "description": "Description",
        "status": "Status",
        "evidence": "Evidence",
        "reasoning": "Reasoning"
    })
    
    # Select and order columns
    display_cols = ["Rule ID", "Description", "Status", "Evidence", "Reasoning"]
    df = df[[col for col in display_cols if col in df.columns]]
    
    # Style function for row highlighting
    def highlight_status(row):
        status = str(row.get("Status", "")).upper()
        if status == "FAIL":
            return ["background-color: #f8d7da"] * len(row)
        elif status == "DATA_GAP":
            return ["background-color: #fff3cd"] * len(row)
        elif status == "PASS":
            return ["background-color: #d4edda"] * len(row)
        return [""] * len(row)
    
    # Apply styling and display
    styled_df = df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        pass_count = len(df[df["Status"].str.upper() == "PASS"])
        st.metric("✅ Passed", pass_count)
    with col2:
        fail_count = len(df[df["Status"].str.upper() == "FAIL"])
        st.metric("❌ Failed", fail_count)
    with col3:
        gap_count = len(df[df["Status"].str.upper() == "DATA_GAP"])
        st.metric("⚠️ Data Gaps", gap_count)


def render_math_validation(data: Dict[str, Any]):
    validation_details = data.get("validation_details", {})
    math_checks = validation_details.get("mathematical_checks", {})
    errors = math_checks.get("errors", [])
    
    st.subheader("🔢 Mathematical Validation Results")
    
    if not errors:
        st.success("✅ All mathematical validations passed!")
        return
    
    # Convert to DataFrame
    rows = []
    for error in errors:
        rows.append({
            "Check Name": error.get("check_name", error.get("name", "Unknown")),
            "Passed": "✅" if error.get("passed", False) else "❌",
            "Message": error.get("message", error.get("error", "N/A"))
        })
    
    df = pd.DataFrame(rows)
    
    # Style function
    def highlight_result(row):
        if row["Passed"] == "❌":
            return ["background-color: #f8d7da"] * len(row)
        return ["background-color: #d4edda"] * len(row)
    
    styled_df = df.style.apply(highlight_result, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Summary
    passed = len([e for e in errors if e.get("passed", False)])
    failed = len(errors) - passed
    st.markdown(f"**Summary:** {passed} passed, {failed} failed out of {len(errors)} checks")


def _convert_rows_to_dataframe(rows, statement_type: str):
    """Convert financial statement rows to a displayable DataFrame."""
    if not rows or not isinstance(rows, list):
        return None
    
    try:
        # Flatten row data for display
        flat_rows = []
        for row in rows:
            if isinstance(row, dict):
                flat_row = {}
                # Get line item name
                flat_row["Line Item"] = row.get("line_item", row.get("name", row.get("particulars", "Unknown")))
                
                # Get values (could be nested dict or direct values)
                values = row.get("values", {})
                if isinstance(values, dict):
                    for key, val in values.items():
                        flat_row[key] = val
                else:
                    flat_row["Value"] = values
                
                # Include note reference if available
                if "note_ref" in row:
                    flat_row["Note"] = row["note_ref"]
                
                flat_rows.append(flat_row)
        
        if flat_rows:
            return pd.DataFrame(flat_rows)
    except Exception as e:
        st.warning(f"Could not convert {statement_type} rows to table: {str(e)}")
    
    return None


def _render_statement_data(statement_data: Dict[str, Any], statement_name: str):
    """Render a single financial statement with appropriate visualization."""
    if not statement_data:
        st.info(f"No {statement_name} data available.")
        return
    
    # Try to extract and display rows as DataFrame
    rows = statement_data.get("rows", [])
    
    if rows:
        df = _convert_rows_to_dataframe(rows, statement_name)
        if df is not None and not df.empty:
            st.markdown(f"**{statement_name} - Line Items**")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            # Fallback to expanded JSON
            st.json(statement_data, expanded=True)
    else:
        # No rows, show full JSON expanded
        st.json(statement_data, expanded=True)
    
    # Show totals if available
    totals = statement_data.get("totals", {})
    if totals:
        st.markdown("**Key Totals:**")
        totals_cols = st.columns(min(len(totals), 4))
        for idx, (key, value) in enumerate(totals.items()):
            col_idx = idx % len(totals_cols)
            with totals_cols[col_idx]:
                if isinstance(value, dict):
                    display_val = value.get("current_year", value.get("value", str(value)))
                else:
                    display_val = value
                st.metric(key.replace("_", " ").title(), display_val)


def render_extracted_data(data: Dict[str, Any]):
    """Render the Extracted Data tab with better visualization."""
    extracted_data = data.get("extracted_data", {})
    
    st.subheader("📦 Extracted Financial Data")
    
    if not extracted_data:
        st.warning("⚠️ No extracted data available. The extraction may have failed.")
        return
    
    # Get individual statement data
    bs_data = extracted_data.get("balance_sheet", {})
    pl_data = extracted_data.get("profit_loss", extracted_data.get("profit_and_loss", {}))
    cf_data = extracted_data.get("cash_flow", {})
    
    # Create nested tabs for each statement
    bs_tab, pl_tab, cf_tab, raw_tab = st.tabs([
        "📊 Balance Sheet",
        "📈 Profit & Loss",
        "💰 Cash Flow",
        "📝 Raw JSON"
    ])
    
    with bs_tab:
        _render_statement_data(bs_data, "Balance Sheet")
    
    with pl_tab:
        _render_statement_data(pl_data, "Profit & Loss")
    
    with cf_tab:
        _render_statement_data(cf_data, "Cash Flow")
    
    with raw_tab:
        st.markdown("**Full Extracted Data (Debug View)**")
        st.json(extracted_data, expanded=True)


def main():
    # Initialize session state
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 📊 NFRA Compliance Engine")
        st.markdown("---")
        
        st.markdown("### Upload Report")
        uploaded_file = st.file_uploader(
            "Select a PDF file",
            type=["pdf"],
            help="Upload an annual report or financial statement PDF"
        )
        
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            st.success(f"📄 {uploaded_file.name}")
            st.caption(f"Size: {uploaded_file.size / 1024:.1f} KB")
        
        st.markdown("---")
        
        analyze_button = st.button(
            "🔍 Analyze Report",
            type="primary",
            use_container_width=True,
            disabled=uploaded_file is None
        )
        
        if analyze_button and uploaded_file:
            with st.spinner("Analyzing report... This may take a few minutes."):
                result = validate_report(uploaded_file)
                st.session_state.analysis_result = result
        
        st.markdown("---")
        
        # Download button placeholder
        if st.session_state.analysis_result and st.session_state.analysis_result.get("success"):
            data = st.session_state.analysis_result["data"]
            report_path = data.get("report_path")
            if report_path:
                st.download_button(
                    "📥 Download Report",
                    data=report_path,
                    file_name="compliance_report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
        
        st.markdown("---")
        st.markdown("##### About")
        st.caption(
            "NFRA Compliance Engine validates financial reports "
            "against regulatory standards and identifies discrepancies."
        )
    
    # Main content area
    st.title("NFRA Compliance Engine Dashboard")
    
    if st.session_state.analysis_result is None:
        # Welcome state
        st.markdown("""
        <div style="text-align: center; padding: 3rem;">
            <h2>Welcome to NFRA Compliance Engine</h2>
            <p style="color: #666; font-size: 1.1rem;">
                Upload a financial report PDF using the sidebar to begin analysis.
            </p>
            <br>
            <p>📄 Supported formats: Annual Reports, Financial Statements (PDF)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature highlights
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            #### 🔍 Smart Extraction
            Automatically extracts Balance Sheet, P&L, and Cash Flow data from PDFs.
            """)
        with col2:
            st.markdown("""
            #### ✅ Compliance Checks
            Validates against regulatory standards and accounting principles.
            """)
        with col3:
            st.markdown("""
            #### 📊 Risk Analysis
            Identifies potential discrepancies and flags critical issues.
            """)
    
    elif not st.session_state.analysis_result.get("success"):
        # Error state
        error_msg = st.session_state.analysis_result.get("error", "Unknown error occurred")
        st.error("❌ Failed to fetch report. Please check the API.")
        st.markdown(f"**Error Details:** {error_msg}")
        st.markdown("Please check that the API server is running and try again.")
        
        if st.button("🔄 Retry"):
            st.session_state.analysis_result = None
            st.rerun()
    
    else:
        # Success state - render dashboard
        data = st.session_state.analysis_result["data"]
        
        # Validate response has data
        if not data:
            st.error("❌ Failed to fetch report. Please check the API.")
            st.markdown("The API returned an empty response.")
            return
        
        # Header with metadata
        metadata = data.get("metadata", {})
        render_header(metadata)
        
        # Assessment Scorecard (using assessment object)
        render_assessment_scorecard(data)
        
        st.markdown("---")
        
        # Tabs for detailed analysis
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Executive Summary",
            "📑 Compliance Audit",
            "🔢 Math Validation",
            "📦 Extracted Data"
        ])
        
        with tab1:
            render_executive_summary(data)
        
        with tab2:
            render_compliance_audit(data)
        
        with tab3:
            render_math_validation(data)
        
        with tab4:
            render_extracted_data(data)
        
        # Footer with analysis timestamp
        st.markdown("---")
        st.caption(f"Analysis completed. Results are based on automated extraction and may require manual verification.")


if __name__ == "__main__":
    main()
