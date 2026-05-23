import os
import requests
import gradio as gr

API_URL = os.getenv("API_URL", "http://localhost:8000")


def register_item(image, description, status):
    if image is None:
        return "Please upload an image."
    if not description.strip():
        return "Please enter a description."
    try:
        with open(image, "rb") as f:
            files = {"image": (os.path.basename(image), f, "image/jpeg")}
            data = {"text": description}
            response = requests.post(
                f"{API_URL}/items/{status}",
                files=files,
                data=data,
            )
        if response.status_code == 200:
            item_id = response.json().get("item_id")
            return f"Registered successfully!\n\n**Item ID:** `{item_id}`"
        else:
            return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Could not connect to the API server."
    except Exception as e:
        return f"Error: {e}"


def find_matches(item_id, k):
    if not item_id.strip():
        return "Please enter an Item ID."
    try:
        res = requests.get(
            f"{API_URL}/items/{item_id}/matches",
            params={"k": int(k)},
        )
        if res.status_code == 200:
            matches = res.json()
            if not matches:
                return "No matches found."
            result = ""
            for i, m in enumerate(matches, 1):
                result += f"**Match {i}**\n"
                result += f"• Score: `{m.get('score', 0):.2f}`\n"
                result += f"• Item ID: `{m.get('item', {}).get('id', 'N/A')}`\n"
                result += f"• Status: `{m.get('item', {}).get('status', 'N/A')}`\n"
                result += f"• Description: {m.get('item', {}).get('user_text', 'N/A')}\n"
                result += f"• Reason: {m.get('reason', 'N/A')}\n\n"
            return result
        else:
            return f"Error {res.status_code}: {res.text}"
    except requests.exceptions.ConnectionError:
        return "Could not connect to the API server."
    except Exception as e:
        return f"Error: {e}"


def list_items(status_filter):
    try:
        params = {}
        if status_filter != "All":
            params["status"] = status_filter
        res = requests.get(f"{API_URL}/items", params=params)
        if res.status_code == 200:
            items = res.json()
            if not items:
                return "No items found."
            result = ""
            for item in items:
                result += f"**ID:** `{item.get('id')}`\n"
                result += f"• Status: `{item.get('status')}`\n"
                result += f"• Description: {item.get('user_text')}\n"
                result += f"• Image: `{item.get('image_path')}`\n\n"
            return result
        else:
            return f"Error {res.status_code}: {res.text}"
    except requests.exceptions.ConnectionError:
        return "Could not connect to the API server."
    except Exception as e:
        return f"Error: {e}"


with gr.Blocks(
    title="Smart Lost & Found",
    theme=gr.themes.Soft(primary_hue="slate", neutral_hue="slate"),
    css="""
        .gradio-container { max-width: 860px !important; margin: auto; padding-top: 1.5rem; }
        h1 { text-align: center; font-size: 1.8rem; margin-bottom: 0.1rem; }
        .subtitle { text-align: center; color: #888; font-size: 0.95rem; margin-bottom: 1.5rem; }
        .gr-button-primary { width: 100%; margin-top: 0.5rem; }
        .gr-tab-item { font-weight: 600; font-size: 0.95rem; }
        footer { display: none !important; }
    """,
) as demo:

    gr.Markdown("# Smart Lost & Found")
    gr.Markdown("<p class='subtitle'>AI-powered item matching system</p>")

    with gr.Tab("Register Item"):
        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                image_input = gr.Image(
                    type="filepath",
                    label="Upload Image (JPG/PNG)",
                    height=240,
                )
            with gr.Column(scale=1):
                status_input = gr.Radio(
                    choices=["lost", "found"],
                    value="lost",
                    label="Item Status",
                )
                desc_input = gr.Textbox(
                    label="Description",
                    placeholder="e.g. Black Nike backpack with a scratch on the left side",
                    lines=3,
                )
                register_btn = gr.Button("Submit Registration", variant="primary")
        register_output = gr.Markdown()
        register_btn.click(
            fn=register_item,
            inputs=[image_input, desc_input, status_input],
            outputs=register_output,
        )

    with gr.Tab("Find Matches"):
        id_input = gr.Textbox(
            label="Item ID",
            placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000",
        )
        k_input = gr.Slider(
            minimum=1, maximum=10, value=3, step=1,
            label="Number of matches (k)",
        )
        search_btn = gr.Button("Search Matches", variant="primary")
        search_output = gr.Markdown()
        search_btn.click(
            fn=find_matches,
            inputs=[id_input, k_input],
            outputs=search_output,
        )

    with gr.Tab("All Items"):
        status_filter = gr.Radio(
            choices=["All", "lost", "found"],
            value="All",
            label="Filter by status",
        )
        list_btn = gr.Button("Refresh List", variant="primary")
        list_output = gr.Markdown()
        list_btn.click(
            fn=list_items,
            inputs=[status_filter],
            outputs=list_output,
        )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)