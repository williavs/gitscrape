import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from github import Github
import base64

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="GitHub & Docs Scraper",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize GitHub client
def init_github_client() -> Github:
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        st.error("GitHub token not found. Please set GITHUB_TOKEN in your .env file.")
        st.stop()
    return Github(github_token)

def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL"""
    try:
        # Clean the URL
        url = url.strip()
        if not url:
            raise ValueError("Please enter a GitHub URL")
            
        # Remove 'https://' or 'http://' if present
        if url.startswith(('https://github.com/', 'http://github.com/')):
            url = url.replace('https://github.com/', '').replace('http://github.com/', '')
        
        # Split remaining path
        parts = url.strip('/').split('/')
        
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL format. Expected format: username/repository")
            
        owner = parts[0]
        repo = parts[1]
        
        if not owner or not repo:
            raise ValueError("Both username and repository name are required")
            
        return owner, repo
        
    except Exception as e:
        raise ValueError(f"Invalid GitHub URL: {str(e)}")

def get_repo_structure(repo, path: str = "") -> List[dict]:
    """Get repository structure as a list of files and directories"""
    items = []
    try:
        contents = repo.get_contents(path)
        for content in contents:
            if content.type == "dir":
                items.append({
                    "path": content.path,
                    "type": "directory",
                    "name": content.name
                })
            elif content.name.endswith(('.md', '.py', '.js', '.tsx', '.ts', '.jsx', '.txt')):
                items.append({
                    "path": content.path,
                    "type": "file",
                    "name": content.name
                })
    except Exception as e:
        st.error(f"Error accessing path {path}: {str(e)}")
    
    return sorted(items, key=lambda x: (x['type'] == 'file', x['path']))

def get_selected_contents(repo, selected_files: List[str]) -> str:
    """Get contents of selected files"""
    contents = []
    for file_path in selected_files:
        try:
            file_content = repo.get_contents(file_path)
            decoded_content = base64.b64decode(file_content.content).decode('utf-8')
            contents.append(f"### File: {file_path}\n\n{decoded_content}\n\n")
        except Exception as e:
            st.warning(f"Could not decode {file_path}: {str(e)}")
    
    return "\n".join(contents)

def main():
    st.title("GitHub & Documentation Scraper")
    
    with st.sidebar:
        st.header("Configuration")
        scrape_type = st.radio(
            "Select Scraping Type",
            ["GitHub Repository", "Documentation Site"]
        )
    
    if scrape_type == "GitHub Repository":
        st.header("GitHub Repository Scraper")
        
        # Add help text
        st.markdown("""
        Enter a GitHub repository URL in one of these formats:
        - https://github.com/username/repository
        - github.com/username/repository
        - username/repository
        """)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            repo_url = st.text_input(
                "GitHub Repository URL",
                placeholder="https://github.com/owner/repo"
            )
            
        with col2:
            output_format = st.selectbox(
                "Output Format",
                ["Plain Text", "Markdown", "JSON"],
                key="output_format_top"
            )
        
        # Add validation before processing
        if repo_url:
            try:
                # Test URL parsing
                owner, repo_name = parse_github_url(repo_url)
                st.success(f"Valid repository format: {owner}/{repo_name}")
                
                # Initialize GitHub client and get repository
                g = init_github_client()
                try:
                    repo = g.get_repo(f"{owner}/{repo_name}")
                    
                    # Get repository structure
                    with st.spinner("Loading repository structure..."):
                        repo_files = get_repo_structure(repo)
                    
                    # Create file selection interface
                    st.subheader("Select Files to Scrape")
                    
                    # Add select all checkbox
                    select_all = st.checkbox("Select All Files")
                    
                    # Create columns for better organization
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        # Create checkboxes for each file/directory
                        selected_files = []
                        current_dir = None
                        
                        for item in repo_files:
                            if item['type'] == 'directory':
                                if current_dir != os.path.dirname(item['path']):
                                    st.markdown(f"**📁 {item['path']}**")
                                    current_dir = os.path.dirname(item['path'])
                            else:
                                # If select all is checked, default to True
                                is_selected = st.checkbox(
                                    f"📄 {item['path']}", 
                                    value=select_all,
                                    key=item['path']
                                )
                                if is_selected:
                                    selected_files.append(item['path'])
                    
                    with col2:
                        # Add file type filters or other options here
                        st.markdown("### Options")
                        st.markdown("Filter options coming soon!")
                    
                    # Only show scrape button if files are selected
                    if selected_files:
                        if st.button("Scrape Selected Files", type="primary"):
                            with st.spinner("Scraping selected files..."):
                                contents = get_selected_contents(repo, selected_files)
                                
                                if contents.strip():
                                    st.success("Scraping completed!")
                                    
                                    # Show preview
                                    with st.expander("Content Preview", expanded=True):
                                        st.text_area("", value=contents, height=400)
                                    
                                    # Download button
                                    st.download_button(
                                        label="Download Results",
                                        data=contents,
                                        file_name=f"{repo_name}_selected_contents.txt",
                                        mime="text/plain"
                                    )
                                else:
                                    st.warning("No content was found in the selected files.")
                    else:
                        st.warning("Please select at least one file to scrape.")
                    
                except Exception as e:
                    if "404" in str(e):
                        st.error(f"Repository not found: {owner}/{repo_name}. Please check:\n"
                               f"1. The repository exists\n"
                               f"2. The repository is public\n"
                               f"3. You have the correct permissions")
                    else:
                        st.error(f"Error accessing repository: {str(e)}")
                
            except ValueError as e:
                st.error(str(e))
    
    else:
        st.header("Documentation Site Scraper")
        st.info("Documentation site scraping functionality coming soon!")

if __name__ == "__main__":
    main()
