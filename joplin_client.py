# joplin_client.py

import requests
import json
import platform
from datetime import datetime
from config import JOPLIN_TOKEN, JOPLIN_API_URL, JOPLIN_NOTEBOOK_NAME

class JoplinClient:
    def __init__(self):
        self.token = JOPLIN_TOKEN
        self.api_url = JOPLIN_API_URL
        self.notebook_id = self._get_notebook_id(JOPLIN_NOTEBOOK_NAME)

    def _get_notebook_id(self, notebook_name):
        """Get the ID of a notebook by name, or create it if it doesn't exist."""
        notebook_id = self._find_notebook_id(notebook_name)
        if notebook_id:
            return notebook_id
        else:
            return self._create_notebook(notebook_name)

    def _find_notebook_id(self, notebook_name):
        """Find a notebook by name."""
        params = {"token": self.token, "page": 1}
        try:
            while True:
                res = requests.get(f"{self.api_url}/folders", params=params)
                res.raise_for_status()
                data = res.json()
                results = data.get('items', [])
                
                for notebook in results:
                    if notebook['title'] == notebook_name:
                        return notebook['id']
                
                if not data.get('has_more'):
                    break
                
                params['page'] += 1
        except requests.exceptions.RequestException as e:
            print(f"Error finding notebook: {e}")
        return None

    def _create_notebook(self, notebook_name):
        """Create a new notebook."""
        params = {"token": self.token}
        body = {"title": notebook_name}
        try:
            res = requests.post(f"{self.api_url}/folders", params=params, json=body)
            res.raise_for_status()
            print(f"Created notebook: {notebook_name}")
            return res.json()['id']
        except requests.exceptions.RequestException as e:
            print(f"Error creating notebook: {e}")
        return None

    def create_or_update_note(self, title, body, parent_id=None, tags=None, append=False):
        """Create a new note or update it if it already exists."""
        note_id = self._find_note_id(title)
        if note_id:
            if append:
                existing_body = self.get_note_body(note_id)
                # Smart Merge Logic:
                # 1. If exactly the same, skip
                if body.strip() == existing_body.strip():
                    print(f"Note '{title}' is already up to date in Joplin.")
                    note_data = {"id": note_id}
                # 2. If existing is a subset of new, use the new one (it's more complete)
                elif existing_body.strip() in body.strip():
                    print(f"New export for '{title}' is more complete. Updating.")
                    note_data = self._update_note(note_id, body)
                # 3. If new is a subset of existing, skip (nothing new to add)
                elif body.strip() in existing_body.strip():
                    print(f"Joplin already has more content for '{title}'. Skipping.")
                    note_data = {"id": note_id}
                # 4. Otherwise, merge them
                else:
                    print(f"Merging content for '{title}' from multiple sources.")
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                    host = platform.node().split('.')[0]
                    new_body = f"{existing_body}\n\n---\n### Merged from {host} on {timestamp}\n\n{body}"
                    note_data = self._update_note(note_id, new_body)
            else:
                note_data = self._update_note(note_id, body)
        else:
            note_data = self._create_note(title, body, parent_id or self.notebook_id)
        
        if note_data and tags:
            self._set_note_tags(note_data['id'], tags)
        return note_data

    def get_note_body(self, note_id):
        """Get the body of a note from Joplin."""
        params = {"token": self.token, "fields": "body"}
        try:
            res = requests.get(f"{self.api_url}/notes/{note_id}", params=params)
            res.raise_for_status()
            return res.json().get('body', '')
        except requests.exceptions.RequestException as e:
            print(f"Error getting note body: {e}")
        return ""

    def _find_note_id(self, title):
        """Find a note by title."""
        params = {"token": self.token, "query": f'title:"{title}"', "type": "note"}
        try:
            res = requests.get(f"{self.api_url}/search", params=params)
            res.raise_for_status()
            results = res.json().get('items', [])
            for note in results:
                if note['title'] == title:
                    return note['id']
        except requests.exceptions.RequestException as e:
            print(f"Error finding note: {e}")
        return None

    def _create_note(self, title, body, parent_id):
        """Create a new note."""
        params = {"token": self.token}
        note_data = {
            "parent_id": parent_id,
            "title": title,
            "body": body,
            "markup_language": 1 # Markdown
        }
        try:
            res = requests.post(f"{self.api_url}/notes", params=params, json=note_data)
            res.raise_for_status()
            print(f"Created note: {title}")
            return res.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating note: {e}")
        return None

    def _update_note(self, note_id, body):
        """Update an existing note."""
        params = {"token": self.token}
        note_data = {"body": body, "markup_language": 1} # Explicitly set Markdown for updates
        try:
            res = requests.put(f"{self.api_url}/notes/{note_id}", params=params, json=note_data)
            res.raise_for_status()
            print(f"Updated note with ID: {note_id}")
            return res.json()
        except requests.exceptions.RequestException as e:
            print(f"Error updating note: {e}")
        return None

    def _find_tag_id(self, tag_title):
        """Find a tag by title, creating it if it doesn't exist."""
        params = {"token": self.token, "query": f'title:"{tag_title}"', "type": "tag"}
        try:
            res = requests.get(f"{self.api_url}/search", params=params)
            res.raise_for_status()
            results = res.json().get('items', [])
            for tag in results:
                if tag['title'] == tag_title:
                    return tag['id']
        except requests.exceptions.RequestException as e:
            print(f"Error finding tag: {e}")
        return None

    def _create_tag(self, tag_title):
        """Create a new tag."""
        params = {"token": self.token}
        tag_data = {"title": tag_title}
        try:
            res = requests.post(f"{self.api_url}/tags", params=params, json=tag_data)
            res.raise_for_status()
            print(f"Created tag: {tag_title}")
            return res.json()['id']
        except requests.exceptions.RequestException as e:
            print(f"Error creating tag: {e}")
        return None

    def _set_note_tags(self, note_id, tag_titles):
        """Set tags for a given note, creating tags if they don't exist."""
        current_tags = self._get_note_tags(note_id)
        current_tag_titles = {tag['title'] for tag in current_tags}

        tags_to_add = []
        for tag_title in tag_titles:
            if tag_title not in current_tag_titles:
                tag_id = self._find_tag_id(tag_title)
                if not tag_id:
                    tag_id = self._create_tag(tag_title)
                tags_to_add.append(tag_id)
        
        # Add new tags to note
        for tag_id in tags_to_add:
            try:
                res = requests.post(f"{self.api_url}/tags/{tag_id}/notes", params={"token": self.token}, json={"id": note_id})
                res.raise_for_status()
                print(f"Added tag to note: {tag_id} -> {note_id}")
            except requests.exceptions.RequestException as e:
                print(f"Error adding tag to note: {e}")

        # Remove tags that are no longer specified
        for tag in current_tags:
            if tag['title'] not in tag_titles:
                try:
                    res = requests.delete(f"{self.api_url}/tags/{tag['id']}/notes", params={"token": self.token}, json={"id": note_id})
                    res.raise_for_status()
                    print(f"Removed tag from note: {tag['id']} -> {note_id}")
                except requests.exceptions.RequestException as e:
                    print(f"Error removing tag from note: {e}")

    def _get_note_tags(self, note_id):
        """Get all tags associated with a note."""
        params = {"token": self.token, "fields": "id,title"}
        try:
            res = requests.get(f"{self.api_url}/notes/{note_id}/tags", params=params)
            res.raise_for_status()
            return res.json()['items']
        except requests.exceptions.RequestException as e:
            print(f"Error getting note tags: {e}")
        return []


if __name__ == '__main__':
    # Example usage
    joplin = JoplinClient()
    if joplin.notebook_id:
        joplin.create_or_update_note("Test Note from Script", "This is a test note.")
