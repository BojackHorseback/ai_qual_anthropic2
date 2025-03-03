import streamlit as st
import hmac
import os
import time
import io
import config
from datetime import datetime
from google.oauth2.service_account import Credentials  # FIXED import
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# Initialize session state variables
if "username" not in st.session_state:
    st.session_state.username = None

SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_ID = "1-y9bGuI0nmK22CPXg804U5nZU3gA--lV"  # Your Google Drive folder ID

def authenticate_google_drive():
    """Authenticate using a service account and return the Google Drive service."""
    key_path = "/etc/secrets/service-account.json"

    if not os.path.exists(key_path):
        raise FileNotFoundError("Google Drive credentials file not found!")

    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def upload_file_to_drive(service, file_path, file_name, mimetype='text/plain'):
    """Upload a file to a specific Google Drive folder."""
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]  # Upload into the correct folder
    }

    with io.FileIO(file_path, 'rb') as file_data:
        media = MediaIoBaseUpload(file_data, mimetype=mimetype)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return file['id']


def save_interview_data_to_drive(transcript_path, time_path):
    """Save interview transcript & timing data to Google Drive."""
    
    if st.session_state.username is None:
        st.error("Username is not set!")
        return

    service = authenticate_google_drive()  # Authenticate Drive API

    try:
        transcript_id = upload_file_to_drive(service, transcript_path, os.path.basename(transcript_path))
        time_id = upload_file_to_drive(service, time_path, os.path.basename(time_path))
        st.success(f"Files uploaded! Transcript ID: {transcript_id}, Time ID: {time_id}")
    except Exception as e:
        st.error(f"Failed to upload files: {e}")


def save_interview_data(username, transcripts_directory, times_directory, file_name_addition_transcript="", file_name_addition_time=""):
    """Write interview data (transcript + timestamps) to a single file."""
    
    # Combine file name with timestamp for uniqueness
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
    file_name = f"{username}_interview_{timestamp}.txt"

    # Set the directory path where the file will be stored
    file_path = os.path.join(transcripts_directory, file_name)

    try:
        with open(file_path, "w") as file:
            # Write the transcript and timestamps
            file.write("Transcript with Timestamps:\n")
            for message in st.session_state.messages:
                message_role = message['role']
                message_content = message['content']
                message_time = time.strftime("%H:%M:%S", time.localtime())  # Timestamp for when message was logged

                file.write(f"{message_role.capitalize()}: {message_content} at {message_time}\n")
            
            # Add the interview start time and duration
            duration = (time.time() - st.session_state.start_time) / 60
            file.write("\nInterview Info:\n")
            file.write(f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n")
            file.write(f"Interview duration (minutes): {duration:.2f}\n")
    
    except Exception as e:
        st.error(f"Error saving interview data: {e}")
        return None

    return file_path


def check_password():
    """Returns 'True' if the user has entered a correct password."""
    def login_form():
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        if st.session_state.username in st.secrets.passwords and hmac.compare_digest(
            st.session_state.password,
            st.secrets.passwords[st.session_state.username],
        ):
            st.session_state.password_correct = True
        else:
            st.session_state.password_correct = False
        del st.session_state.password  # Don't store password in session state

    if st.session_state.get("password_correct", False):
        return True, st.session_state.username

    login_form()
    if "password_correct" in st.session_state:
        st.error("User or password incorrect")
    return False, st.session_state.username


def check_if_interview_completed(directory, username):
    """Check if interview transcript/time file exists."""
    if username != "testaccount":
        return os.path.exists(os.path.join(directory, f"{username}.txt"))
    return False
