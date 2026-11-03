"""
Module: MIN-DISC SaaS Dashboard Design System & Styles
Defines unified CSS styles for professional SaaS visual appearance:
- White background with high-contrast slate and navy typography.
- Navy-blue primary theme (#0F294A / #1E3A8A).
- Dark green indicators for success (#15803D / #F0FDF4).
- Red indicators for blocked status (#DC2626 / #FEF2F2).
- Amber indicators for review and pending status (#D97706 / #FFFBEB).
"""

SAAS_CSS = """
<style>
    /* Global Container Spacing */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1260px;
    }

    /* Top Brand Header */
    .brand-header {
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 1.1rem;
        margin-bottom: 1.5rem;
    }
    .brand-title {
        font-size: 1.85rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.025em;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .brand-subtitle {
        font-size: 0.95rem;
        color: #475569;
        margin-bottom: 0.85rem;
    }
    .brand-axiom {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #1E3A8A;
        border-radius: 6px;
        padding: 10px 16px;
        color: #1E293B;
        font-size: 0.90rem;
        line-height: 1.5;
        margin-bottom: 1rem;
    }
    .brand-axiom b {
        color: #0F172A;
    }

    /* Workflow Cards on Landing Dashboard */
    .workflow-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    .workflow-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 24px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .workflow-card:hover {
        border-color: #CBD5E1;
        box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.06);
    }
    .workflow-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .workflow-desc {
        font-size: 0.90rem;
        color: #475569;
        margin-bottom: 1rem;
        line-height: 1.5;
    }
    .workflow-meta-item {
        font-size: 0.84rem;
        color: #334155;
        margin-bottom: 0.4rem;
    }

    /* Stage Containers */
    .stage-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px 22px;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    }
    .stage-title {
        font-size: 1.12rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .stage-badge {
        font-size: 0.70rem;
        font-weight: 700;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 4px;
        background-color: #EFF6FF;
        color: #1E40AF;
        letter-spacing: 0.05em;
    }

    /* Policy Outcome Banners */
    .card-passed {
        background-color: #F0FDF4;
        border: 1px solid #86EFAC;
        border-left: 5px solid #15803D;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 1.2rem;
        color: #14532D;
    }
    .card-blocked {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 5px solid #DC2626;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 1.2rem;
        color: #7F1D1D;
    }
    .card-review {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 5px solid #D97706;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 1.2rem;
        color: #78350F;
    }

    /* Status Pills */
    .pill-active {
        background-color: #DCFCE7;
        color: #15803D;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 9999px;
    }
    .pill-pending {
        background-color: #FEF3C7;
        color: #B45309;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 9999px;
    }
    .pill-blocked {
        background-color: #FEE2E2;
        color: #B91C1C;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 9999px;
    }

    /* Informational Tables and Key-Value Lists */
    .kv-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.88rem;
    }
    .kv-table td {
        padding: 8px 12px;
        border-bottom: 1px solid #F1F5F9;
    }
    .kv-table tr:last-child td {
        border-bottom: none;
    }
    .kv-key {
        color: #475569;
        font-weight: 600;
        width: 32%;
    }
    .kv-val {
        color: #0F172A;
    }

    /* Sidebar info box */
    .sidebar-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 12px 14px;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        color: #334155;
    }
    .sidebar-card b {
        color: #0F172A;
    }

    /* Demonstration Notice */
    .demo-notice {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 0.83rem;
        color: #475569;
        margin-bottom: 1rem;
    }
</style>
"""


def apply_saas_styles():
    """Injects SaaS CSS styles into the current Streamlit page."""
    import streamlit as st
    st.markdown(SAAS_CSS, unsafe_allow_html=True)
