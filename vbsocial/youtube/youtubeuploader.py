import os
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from tqdm import tqdm


class YouTubeUploader:
    def __init__(self, credentials):
        self.credentials = credentials
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", credentials=self.credentials)

    def read_metadata(self, metadata_file):
        """Read metadata from JSON file."""
        with open(metadata_file, 'r') as f:
            return json.load(f)

    def read_file(self, file_path):
        """Read content from a text file."""
        with open(file_path, 'r') as f:
            return f.read().strip()

    def upload(self, metadata_file, privacy_status="private"):
        try:
            # Read metadata
            metadata = self.read_metadata(metadata_file)

            # Read description from file
            with open(metadata['files']['description'], 'r') as f:
                description = f.read().strip()

            # Map license value
            license_map = {
                "Standard YouTube License": "youtube",
                "Creative Commons": "creativeCommons"
            }

            # Prepare the video insert request
            request_body = {
                "snippet": {
                    "title": metadata.get('title', ''),
                    "description": description,
                    "tags": metadata.get('tags', []),
                    "categoryId": "27",  # Education category
                    "defaultLanguage": metadata['language']['video']
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "license": license_map.get(metadata.get('license'), 'youtube'),
                    "embeddable": metadata.get('embedding', True),
                    "selfDeclaredMadeForKids": False
                },
                "recordingDetails": {
                    "recordingDate": metadata['recording'].get('date'),
                    "location": {
                        "description": metadata['recording'].get('location')
                    }
                }
            }

            media = MediaFileUpload(
                metadata['files']['video'],
                chunksize=1024 * 1024,  # 1MB chunks
                resumable=True,
                mimetype='video/*'
            )

            request = self.youtube.videos().insert(
                part="snippet,status,recordingDetails",
                body=request_body,
                media_body=media
            )

            # Create progress bar
            with tqdm(total=100, desc="Uploading", unit="%", ncols=100) as pbar:
                response = None
                last_progress = 0
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        if progress > last_progress:
                            pbar.update(progress - last_progress)
                            last_progress = progress

            print("\nUpload completed successfully!")

            # Get video ID and create URL
            video_id = response['id']
            video_url = f"https://youtu.be/{video_id}"

            # Save video ID to metadata
            metadata['youtube_id'] = video_id
            metadata['url'] = video_url  # Also save URL in metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=4)

            print(f"Video ID: {video_id}")
            print(f"Video URL: {video_url}")

            # Now proceed with additional operations
            try:
                # Update thumbnail if provided
                if 'thumbnail' in metadata['files']:
                    self.set_thumbnail(
                        video_id, metadata['files']['thumbnail'])

                # Update education metadata
                if 'education' in metadata:
                    self.update_video_settings(video_id, metadata)
            except Exception as e:
                print(f"Warning: Some post-upload operations failed: {e}")
                print("But don't worry, your video is uploaded and the ID is saved!")

            return response

        except HttpError as err:
            print(f"An error occurred: {err}")
            return None

    def update_video_settings(self, video_id, metadata):
        """Update additional video settings after upload."""
        try:
            if 'education' in metadata:
                # Generate education-related tags
                education_info = metadata['education']
                # Changed from metadata['video'].get('tags', [])
                base_tags = metadata.get('tags', [])

                education_tags = base_tags + [
                    education_info.get('academic_system', ''),  # e.g., "India"
                    # e.g., "Intermediate"
                    education_info.get('level', ''),
                    # e.g., "JEE Advanced"
                    education_info.get('exam', ''),
                    # e.g., "Problem walkthrough"
                    education_info.get('type', '')
                ]
                # Clean up tags (remove empty strings and duplicates)
                education_tags = list(
                    set(tag for tag in education_tags if tag))

                # Prepare update body
                update_body = {
                    "id": video_id,
                    "snippet": {
                        "categoryId": "27",  # Education category
                        "title": self.youtube.videos().list(
                            part="snippet",
                            id=video_id
                        ).execute()['items'][0]['snippet']['title'],
                        "description": self.youtube.videos().list(
                            part="snippet",
                            id=video_id
                        ).execute()['items'][0]['snippet']['description'],
                        "tags": education_tags
                    }
                }

                # Add education info to description
                education_section = "\n\n=== Education Information ===\n"
                education_section += f"Type: {education_info.get('type', 'N/A')}\n"
                education_section += f"Academic System: {education_info.get('academic_system', 'N/A')}\n"
                education_section += f"Level: {education_info.get('level', 'N/A')}\n"
                education_section += f"Exam: {education_info.get('exam', 'N/A')}\n"

                # Add problems if they exist
                if 'problems' in education_info:
                    education_section += "\nProblems Covered:\n"
                    for problem in education_info['problems']:
                        education_section += f"• {problem}\n"

                # Append education info to existing description
                update_body["snippet"]["description"] += education_section

                # Update video with all information
                self.youtube.videos().update(
                    part="snippet",
                    body=update_body
                ).execute()

                print(
                    "Education information added to description and tags successfully!")

        except HttpError as e:
            print(f"Error updating video settings: {e}")

    def set_thumbnail(self, video_id, thumbnail_path):
        try:
            # For thumbnails, we don't need chunking since they're small
            media = MediaFileUpload(
                thumbnail_path,
                mimetype='image/png',
                resumable=False  # Changed to False for direct upload
            )

            print("Uploading thumbnail...")
            response = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()

            print("Thumbnail uploaded successfully!")

        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def update_video_by_id(self, metadata_file):
        """Update an existing video using metadata file."""
        try:
            # Read metadata
            metadata = self.read_metadata(metadata_file)

            if 'youtube_id' not in metadata:
                raise ValueError("No YouTube ID found in metadata file")

            video_id = metadata['youtube_id']

            # Read description from file
            with open(metadata['files']['description'], 'r') as f:
                description = f.read().strip()

            # Prepare update body with all metadata
            update_body = {
                "id": video_id,
                "snippet": {
                    "title": metadata.get('title', ''),
                    "description": description,
                    "tags": metadata.get('tags', []),
                    "categoryId": "27",  # Education category
                    "defaultLanguage": metadata['language']['video']
                }
            }

            # Update video metadata
            self.youtube.videos().update(
                part="snippet",
                body=update_body
            ).execute()

            print(f"Video metadata updated successfully!")

            # Update thumbnail if provided
            if 'thumbnail' in metadata['files']:
                try:
                    self.set_thumbnail(
                        video_id, metadata['files']['thumbnail'])
                    print("Thumbnail updated successfully!")
                except Exception as e:
                    print(f"Error updating thumbnail: {e}")

            # Update education metadata
            if 'education' in metadata:
                self.update_video_settings(video_id, metadata)

        except Exception as e:
            print(f"Error updating video: {e}")
