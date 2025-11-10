def get_html_content(recipient_name="", recipient_data=None):
    """Renders the HTML email body from a Jinja2 template."""
    if not os.path.exists(HTML_TEMPLATE_FILE):
        logging.error(f"HTML template file '{HTML_TEMPLATE_FILE}' not found.")
        return None
    try:
        template_dir = os.path.dirname(os.path.abspath(HTML_TEMPLATE_FILE)) or '.'
        template_name = os.path.basename(HTML_TEMPLATE_FILE)
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_name)
        
        template_vars = {
            'recipient': recipient_name,
            'sender_name': SENDER_NAME,
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'current_year': datetime.now().year
        }
        if recipient_data:
            template_vars.update(recipient_data)
        
        return template.render(template_vars)
    except Exception as e:
        logging.error(f"Error rendering Jinja2 template: {e}")
        return None
    
if __name__== "__main__":
    create_log_file()