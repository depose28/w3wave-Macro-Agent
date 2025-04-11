import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, Optional
import json

# Load environment variables
load_dotenv()
TOKEN_TERMINAL_API_KEY = os.getenv("TOKEN_TERMINAL_API_KEY")
if not TOKEN_TERMINAL_API_KEY:
    raise ValueError("TOKEN_TERMINAL_API_KEY not found in .env file")

BASE_URL = "https://api.tokenterminal.com/v2"

def fetch_fluid_metrics() -> Optional[Dict]:
    """Fetch metrics for Fluid (formerly Instadapp) from Token Terminal API.
    
    Returns:
        Dict containing metrics if successful, None if there was an error
    """
    try:
        headers = {
            "Authorization": f"Bearer {TOKEN_TERMINAL_API_KEY}"
        }
        
        # First, let's get the list of available projects
        projects_response = requests.get(
            f"{BASE_URL}/projects",
            headers=headers
        )
        
        if projects_response.status_code != 200:
            print(f"❌ Error fetching projects list: {projects_response.status_code} - {projects_response.text}")
            return None
            
        # Try to find Fluid/Instadapp in the projects list
        projects = projects_response.json()
        if isinstance(projects, list):
            # Look for project with project_id "instadapp"
            project = next((p for p in projects if isinstance(p, dict) and p.get("project_id") == "instadapp"), None)
            
            if not project:
                print("❌ Project not found with project_id 'instadapp'")
                return None
                
            print(f"✅ Found project: {project.get('name')} (ID: {project.get('project_id')})")
            
            # Now fetch metrics for the correct project ID
            response = requests.get(
                f"{BASE_URL}/projects/instadapp/metrics",
                headers=headers
            )
            
            if response.status_code == 200:
                metrics = response.json()
                print("Raw metrics:", json.dumps(metrics, indent=2))  # Debug print
                return metrics
            else:
                print(f"❌ Error fetching metrics: {response.status_code} - {response.text}")
                return None
        else:
            print("❌ Unexpected response format from Token Terminal API")
            return None
            
    except Exception as e:
        print(f"❌ Exception while fetching metrics: {e}")
        return None

def format_metrics_for_email(metrics: Dict) -> str:
    """Format metrics into a readable string for email.
    
    Args:
        metrics: Dictionary containing Fluid metrics
    
    Returns:
        Formatted string for email
    """
    if not metrics:
        return "📊 Fluid Metrics: No data available"
    
    # Format numbers with commas and dollar signs where appropriate
    formatted_metrics = []
    
    # Helper function to format currency values
    def format_currency(value: float) -> str:
        return f"${value:,.2f}"
    
    # Helper function to format large numbers
    def format_number(value: float) -> str:
        return f"{value:,.0f}"
    
    # Add each metric with appropriate formatting
    if "revenue" in metrics:
        formatted_metrics.append(f"- Revenue: {format_currency(metrics['revenue'])}")
    if "fees" in metrics:
        formatted_metrics.append(f"- Fees: {format_currency(metrics['fees'])}")
    if "tvl" in metrics:
        formatted_metrics.append(f"- TVL: {format_currency(metrics['tvl'])}")
    if "active_users" in metrics:
        formatted_metrics.append(f"- Active Users: {format_number(metrics['active_users'])}")
    if "token_emissions" in metrics:
        formatted_metrics.append(f"- Token Emissions: {format_number(metrics['token_emissions'])}")
    if "market_cap" in metrics:
        formatted_metrics.append(f"- Market Cap: {format_currency(metrics['market_cap'])}")
    if "pe_ratio" in metrics:
        formatted_metrics.append(f"- P/E Ratio: {metrics['pe_ratio']:.2f}")
    
    return "📊 Fluid Metrics:\n" + "\n".join(formatted_metrics) 