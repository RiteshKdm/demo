import streamlit as st
import json
from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment or Streamlit secrets
api_key = os.getenv('GROQ_API_KEY') or st.secrets["GROQ_API_KEY"]

# Initialize Groq client
try:
    client = Groq(api_key=api_key)
except Exception as e:
    st.error("Failed to initialize Groq client. Please check your API key.")
    st.stop()



def summarize_with_llm(text):
    prompt = f"Please provide a concise summary of the following text in steps:\n\n{text}"
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that provides concise summaries."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=150
    )
    
    return completion.choices[0].message.content

def process_selected_component(json_data, selected_component, additional_text):
    """Process and summarize data for a specific component"""
    try:
        # Aggregate comments for all issues with the same component name
        aggregated_comments = []
        for item in json_data:
            if item['Component'].lower() == selected_component.lower():
                for comment_obj in item.get('Comment', []):
                    aggregated_comments.append(comment_obj.get('comment', ''))
        
        if aggregated_comments:
            # Combine all aggregated comments into a single string
            comments_text = '\n'.join(aggregated_comments)
            
            # Include additional text in the summary
            combined_text = comments_text + "\n\n" + additional_text
            
            # Generate summary using LLM
            component_analysis = summarize_with_llm(combined_text)
            
            return {
                'Component': selected_component,
                'Analysis': component_analysis
            }
        else:
            return None
            
    except Exception as e:
        st.error(f"Error processing component: {str(e)}")
        return None

def normalize_field_name(field_name, data):
    """Helper function to find field regardless of case"""
    if field_name in data:
        return data[field_name]
    # Try case-insensitive match
    for key in data:
        if key.lower() == field_name.lower():
            return data[key]
    return 'N/A'

def format_comments(comments):
    """Format comments into a readable string with line breaks"""
    formatted_comments = []
    for i, c in enumerate(comments, 1):
        comment_text = c['comment'].replace('\n', ' ')
        # Truncate long comments
        if len(comment_text) > 100:
            comment_text = comment_text[:97] + "..."
        formatted_comments.append(f"{i}. {comment_text}")
    return "\n".join(formatted_comments)

def main():
    st.title("JSON Content Summarizer")
    st.write("Upload a JSON file to get summaries of components, comments, and summary fields.")
    
    # File uploader for JSON files
    uploaded_file = st.file_uploader("Choose a JSON file", type=['json'])
    
    if uploaded_file is not None:
        try:
            # Load JSON data from the uploaded file
            json_data = json.load(uploaded_file)
            
            # Add component selector with unique case-insensitive components
            components = sorted(list(set(item['Component'].lower() for item in json_data)))
            selected_component = st.selectbox(
                "🔍 Select a Component to Display",
                options=components,
                format_func=lambda x: x.title()  # Display components in title case
            )
            
            # Filter JSON data to only include the selected component
            filtered_data = [item for item in json_data if item['Component'].lower() == selected_component.lower()]
            
            if filtered_data:
                # Display JSON data in table format
                st.subheader(f"📋 JSON Content Preview for Component: {selected_component.title()}")
                # Convert JSON to a format suitable for table display
                table_data = []
                for item in filtered_data:
                    # Use case-insensitive field matching
                    created_on = normalize_field_name('createdon', item)
                    updated_on = normalize_field_name('updatedon', item)
                    formatted_comments = format_comments(item['Comment'])
                    
                    table_data.append({
                        'JIRA ID': normalize_field_name('jiraid', item),
                        'Component': normalize_field_name('component', item),
                        'Summary': normalize_field_name('summary', item),
                        'Description': (normalize_field_name('description', item)[:100] + "..." 
                                      if len(normalize_field_name('description', item)) > 100 
                                      else normalize_field_name('description', item)),
                        'Created On': created_on,
                        'Updated On': updated_on,
                        'Comments': formatted_comments
                    })
                
                # Display as a scrollable table with adjusted column config
                st.dataframe(
                    table_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Comments": st.column_config.TextColumn(
                            "Comments",
                            width="large",
                            help="Comment history"
                        ),
                        "Description": st.column_config.TextColumn(
                            "Description",
                            width="medium"
                        )
                    }
                )
                
                # Add a separator
                st.markdown("---")
                
                # Textbox for additional text input
                additional_text = st.text_area("📝 Additional Text to Include in Summary", "")
                
                # Component-specific analysis button
                if st.button("🎯 Summarize Selected Component"):
                    with st.spinner('Analyzing selected component...'):
                        result = process_selected_component(json_data, selected_component, additional_text)
                        if result:
                            with st.expander(f"📊 Analysis for {result['Component']}"):
                                st.write(result['Analysis'])
            else:
                st.warning("No data found for the selected component.")
                    
        except json.JSONDecodeError:
            st.error("Error: Invalid JSON file")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
