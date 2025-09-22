import streamlit as st
import sys
import os
from pathlib import Path

# Add current directory to Python path to find modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the modules directly
import byte_extractor_service
import logger_config

# Get the required functions and variables
collection = byte_extractor_service.collection
get_paginated_bytes_with_query = byte_extractor_service.get_paginated_bytes_with_query
update_summary_review_status = byte_extractor_service.update_summary_review_status
update_original_article_review_status = byte_extractor_service.update_original_article_review_status
logger = logger_config.logger

# -------------------------
# Streamlit Page Config
# -------------------------
logger.info("Initializing Heartfulness Article Viewer application")
st.set_page_config(
    page_title="Heartfulness Article Viewer",
    page_icon="📖",
    layout="wide"
)
logger.info("Streamlit page configuration set successfully")

# -------------------------
# Sidebar
# -------------------------
logger.info("Setting up sidebar navigation")
st.sidebar.title("📚 Heartfulness Extractor")
page = st.sidebar.radio("Navigation", [
    "📂 View Extracted Articles"
])
logger.info(f"Selected page: {page}")



# -------------------------
# View Extracted Articles
# -------------------------
if page == "📂 View Extracted Articles":
    logger.info("Rendering View Extracted Articles page")
    st.title("📂 View Extracted Articles from MongoDB")

    # Search and Filter Section
    st.markdown("### 🔍 Search & Filter Articles")
    logger.info("Setting up search and filter section")
    
    # First row: Author multi-select filter
    logger.info("Fetching available authors from database")
    available_authors = sorted(collection.distinct("Author"))
    logger.info(f"Found {len(available_authors)} authors: {available_authors}")
    
    if available_authors:
        selected_authors = st.multiselect(
            "✍️ Select Authors:",
            available_authors,
            default=[],
            help="Select one or more authors to filter articles. Leave empty to show all authors."
        )
        logger.info(f"Selected authors: {selected_authors}")
    else:
        selected_authors = []
        st.warning("No author data found in the database")
        logger.warning("No author data found in the database")
    
    # Second row: Other filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        summary_status_filter = st.selectbox(
            "📊 Summary Review Status:",
            ["All", "🟡 Pending", "🟢 Accepted", "🔴 Rejected"],
            help="Filter articles by their summary review status"
        )
        logger.info(f"Summary status filter selected: {summary_status_filter}")
    
    with col2:
        original_article_status_filter = st.selectbox(
            "📄 Original Article Review Status:",
            ["All", "🟡 Pending", "🟢 Accepted", "🔴 Rejected"],
            help="Filter articles by their original article review status"
        )
        logger.info(f"Original article status filter selected: {original_article_status_filter}")
    
    with col3:
        best_byte_filter = st.selectbox(
            "⭐ Best Byte:",
            ["All", "✅ Yes", "❌ No"],
            help="Filter articles by their best byte status"
        )
        logger.info(f"Best byte filter selected: {best_byte_filter}")
    
    # First dropdown: Year
    logger.info("Fetching available years from database")
    available_years = sorted(collection.distinct("Year"), reverse=True)
    logger.info(f"Found {len(available_years)} years: {available_years}")
    
    if available_years:
        selected_year = st.selectbox("📅 Select Year:", ["All Years"] + available_years)
        logger.info(f"Year selected: {selected_year}")
    else:
        selected_year = "All Years"
        st.warning("No year data found in the database")
        logger.warning("No year data found in the database")
    
    # Second dropdown: Have Summary (independent of year selection)
    logger.info("Processing summary filter across all years")
    
    # Build base query for summary counting (excluding year filter)
    base_query = {}
    if selected_authors:
        base_query["Author"] = {"$in": selected_authors}
    
    # Count documents with and without content_summary across all years
    logger.debug(f"Base query for summary counting: {base_query}")
    all_docs = list(collection.find(base_query, {"content_summary": 1}))
    logger.info(f"Found {len(all_docs)} documents for summary counting")
    
    # Count documents with and without content_summary
    has_summary_count = sum(1 for doc in all_docs if doc.get('content_summary'))
    no_summary_count = len(all_docs) - has_summary_count
    logger.info(f"Summary counts - Has summary: {has_summary_count}, No summary: {no_summary_count}")
    
    summary_options = []
    if has_summary_count > 0:
        summary_options.append(f"✅ Yes ({has_summary_count} articles)")
    if no_summary_count > 0:
        summary_options.append(f"❌ No ({no_summary_count} articles)")
    
    if summary_options:
        selected_summary = st.selectbox("📝 Have Summary:", ["All"] + summary_options)
        logger.info(f"Summary filter selected: {selected_summary}")
    else:
        selected_summary = "All"
        st.warning("No articles found in the database")
        logger.warning("No articles found in the database")
    
    # Third dropdown: Available Editions (based on ALL selected filters)
    # Check if any filters are applied
    any_filters_applied = (
        selected_authors or 
        summary_status_filter != "All" or 
        original_article_status_filter != "All" or
        selected_year != "All Years" or 
        selected_summary != "All"
    )
    
    if any_filters_applied:
        logger.info(f"Processing PDF selection with filters - Authors: {selected_authors}, Summary Status: {summary_status_filter}, Original Article Status: {original_article_status_filter}, Year: {selected_year}, Summary: {selected_summary}")
        
        # Build comprehensive query based on ALL selections
        query = {}
        
        # Add author filter if selected
        if selected_authors:
            query["Author"] = {"$in": selected_authors}
        
        # Add year filter if selected
        if selected_year != "All Years":
            query["Year"] = selected_year
        
        # Add summary filter if selected
        if selected_summary != "All":
            want_summary = selected_summary.startswith("✅")
            logger.info(f"Want summary: {want_summary}")
            if want_summary:
                query["content_summary"] = {"$exists": True, "$ne": ""}
            else:
                query["$or"] = [
                    {"content_summary": {"$exists": False}},
                    {"content_summary": ""},
                    {"content_summary": None}
                ]
        
        # Add summary review status filter if selected
        if summary_status_filter != "All":
            if summary_status_filter == "🟡 Pending":
                query["$or"] = [
                    {"summary_review_status": {"$exists": False}},
                    {"summary_review_status": None},
                    {"summary_review_status": ""},
                    {"summary_review_status": "pending"}
                ]
            elif summary_status_filter == "🟢 Accepted":
                query["summary_review_status"] = "accepted"
            elif summary_status_filter == "🔴 Rejected":
                query["summary_review_status"] = "rejected"
        
        # Add original article review status filter if selected
        if original_article_status_filter != "All":
            if original_article_status_filter == "🟡 Pending":
                query["$or"] = [
                    {"orgnl_artcl_rv_sts": {"$exists": False}},
                    {"orgnl_artcl_rv_sts": None},
                    {"orgnl_artcl_rv_sts": ""},
                    {"orgnl_artcl_rv_sts": "pending"}
                ]
            elif original_article_status_filter == "🟢 Accepted":
                query["orgnl_artcl_rv_sts"] = "accepted"
            elif original_article_status_filter == "🔴 Rejected":
                query["orgnl_artcl_rv_sts"] = "rejected"
        
        logger.debug(f"PDF selection query: {query}")
        
        # Get unique pdf_names for the filtered documents
        available_editions = sorted(collection.distinct("pdf_name", query))
        logger.info(f"Found {len(available_editions)} editions: {available_editions}")
        
        if available_editions:
            selected_pdf = st.selectbox("📚 Select Available Editions:", ["All"] + available_editions)
            logger.info(f"PDF selected: {selected_pdf}")
        else:
            selected_pdf = "All"
            st.warning("No editions found matching the selected criteria")
            logger.warning("No editions found matching the selected criteria")
    else:
        # Fallback to original behavior when no specific filters are applied
        logger.info("Using fallback PDF selection (no filters applied)")
        pdf_names = collection.distinct("pdf_name")
        logger.info(f"Found {len(pdf_names)} total PDFs: {pdf_names}")
        selected_pdf = st.selectbox("📚 Select PDF:", ["All"] + pdf_names)
        logger.info(f"PDF selected: {selected_pdf}")

    # Reset to page 1 if PDF selection changes
    logger.info("Managing pagination state")
    if "last_selected_pdf" not in st.session_state:
        st.session_state.last_selected_pdf = selected_pdf
        logger.info(f"Initializing last_selected_pdf: {selected_pdf}")
    if st.session_state.last_selected_pdf != selected_pdf:
        logger.info(f"PDF selection changed from {st.session_state.last_selected_pdf} to {selected_pdf}, resetting to page 1")
        st.session_state.page_number = 1
        st.session_state.last_selected_pdf = selected_pdf

    # Initialize session state for pagination
    if "page_number" not in st.session_state:
        st.session_state.page_number = 1
        logger.info("Initializing page_number to 1")
    
    logger.info(f"Current page number: {st.session_state.page_number}")

    # --- NAVIGATION HANDLERS (UPDATE STATE FIRST) ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅ Previous", key="prev_top") and st.session_state.page_number > 1:
            logger.info(f"Previous button clicked, changing page from {st.session_state.page_number} to {st.session_state.page_number - 1}")
            st.session_state.page_number -= 1
    with col3:
        if st.button("Next ➡", key="next_top"):
            logger.info(f"Next button clicked, changing page from {st.session_state.page_number} to {st.session_state.page_number + 1}")
            st.session_state.page_number += 1

    # Now fetch results AFTER navigation update
    logger.info("Building final MongoDB query based on all filter selections")
    
    # Build the final query based on all selections
    final_query = {}
    
    # Build conditions for different filters
    status_conditions = []
    original_article_status_conditions = []
    summary_conditions = []
    author_conditions = []
    
    # Apply author filter
    if selected_authors:
        logger.info(f"Applying author filter: {selected_authors}")
        author_conditions = [{"Author": {"$in": selected_authors}}]
        logger.debug(f"Author condition: Author in {selected_authors}")
    
    # Apply summary review status filter
    if summary_status_filter != "All":
        logger.info(f"Applying summary review status filter: {summary_status_filter}")
        if summary_status_filter == "🟡 Pending":
            # For pending, include articles that don't have the field or have "pending" status
            status_conditions = [
                {"summary_review_status": {"$exists": False}},
                {"summary_review_status": None},
                {"summary_review_status": ""},
                {"summary_review_status": "pending"}
            ]
            logger.debug("Pending status conditions: includes missing, null, empty, and 'pending' status")
        elif summary_status_filter == "🟢 Accepted":
            status_conditions = [{"summary_review_status": "accepted"}]
            logger.debug("Accepted status condition: exact match 'accepted'")
        elif summary_status_filter == "🔴 Rejected":
            status_conditions = [{"summary_review_status": "rejected"}]
            logger.debug("Rejected status condition: exact match 'rejected'")
    
    # Apply original article review status filter
    if original_article_status_filter != "All":
        logger.info(f"Applying original article review status filter: {original_article_status_filter}")
        if original_article_status_filter == "🟡 Pending":
            # For pending, include articles that don't have the field or have "pending" status
            original_article_status_conditions = [
                {"orgnl_artcl_rv_sts": {"$exists": False}},
                {"orgnl_artcl_rv_sts": None},
                {"orgnl_artcl_rv_sts": ""},
                {"orgnl_artcl_rv_sts": "pending"}
            ]
            logger.debug("Original article pending status conditions: includes missing, null, empty, and 'pending' status")
        elif original_article_status_filter == "🟢 Accepted":
            original_article_status_conditions = [{"orgnl_artcl_rv_sts": "accepted"}]
            logger.debug("Original article accepted status condition: exact match 'accepted'")
        elif original_article_status_filter == "🔴 Rejected":
            original_article_status_conditions = [{"orgnl_artcl_rv_sts": "rejected"}]
            logger.debug("Original article rejected status condition: exact match 'rejected'")
    
    # Apply best byte filter
    best_byte_conditions = []
    if best_byte_filter != "All":
        logger.info(f"Applying best byte filter: {best_byte_filter}")
        if best_byte_filter == "✅ Yes":
            best_byte_conditions = [{"Best_byte": True}]
            logger.debug("Best byte condition: True")
        elif best_byte_filter == "❌ No":
            best_byte_conditions = [{"Best_byte": False}]
            logger.debug("Best byte condition: False")
    
    # Apply summary filter (independent of year selection)
    if selected_summary != "All":
        logger.info(f"Applying summary filter: {selected_summary}")
        want_summary = selected_summary.startswith("✅")
        if want_summary:
            summary_conditions = [{"content_summary": {"$exists": True, "$ne": ""}}]
            logger.debug("Summary condition: has non-empty content_summary")
        else:
            summary_conditions = [
                {"content_summary": {"$exists": False}},
                {"content_summary": ""},
                {"content_summary": None}
            ]
            logger.debug("Summary condition: missing, empty, or null content_summary")
    
    # Combine conditions using $and with $or arrays
    and_conditions = []
    
    if author_conditions:
        if len(author_conditions) == 1:
            and_conditions.append(author_conditions[0])
            logger.debug("Added single author condition")
        else:
            and_conditions.append({"$or": author_conditions})
            logger.debug(f"Added $or author conditions: {len(author_conditions)} conditions")
    
    if status_conditions:
        if len(status_conditions) == 1:
            and_conditions.append(status_conditions[0])
            logger.debug("Added single status condition")
        else:
            and_conditions.append({"$or": status_conditions})
            logger.debug(f"Added $or status conditions: {len(status_conditions)} conditions")
    
    if original_article_status_conditions:
        if len(original_article_status_conditions) == 1:
            and_conditions.append(original_article_status_conditions[0])
            logger.debug("Added single original article status condition")
        else:
            and_conditions.append({"$or": original_article_status_conditions})
            logger.debug(f"Added $or original article status conditions: {len(original_article_status_conditions)} conditions")
    
    if summary_conditions:
        if len(summary_conditions) == 1:
            and_conditions.append(summary_conditions[0])
            logger.debug("Added single summary condition")
        else:
            and_conditions.append({"$or": summary_conditions})
            logger.debug(f"Added $or summary conditions: {len(summary_conditions)} conditions")
    
    if best_byte_conditions:
        if len(best_byte_conditions) == 1:
            and_conditions.append(best_byte_conditions[0])
            logger.debug("Added single best byte condition")
        else:
            and_conditions.append({"$or": best_byte_conditions})
            logger.debug(f"Added $or best byte conditions: {len(best_byte_conditions)} conditions")
    
    # Apply year filter
    if selected_year != "All Years":
        and_conditions.append({"Year": selected_year})
        logger.debug(f"Added year filter: {selected_year}")
    
    # Apply PDF filter
    if selected_pdf != "All":
        and_conditions.append({"pdf_name": selected_pdf})
        logger.debug(f"Added PDF filter: {selected_pdf}")
    
    # Build final query
    if and_conditions:
        if len(and_conditions) == 1:
            final_query = and_conditions[0]
            logger.debug("Final query: single condition")
        else:
            final_query = {"$and": and_conditions}
            logger.debug(f"Final query: $and with {len(and_conditions)} conditions")
    else:
        logger.info("No filters applied, using empty query (all documents)")
    
    logger.info(f"Final MongoDB query: {final_query}")
    
    # Get paginated results with the final query
    logger.info(f"Fetching paginated results for page {st.session_state.page_number}")
    result = get_paginated_bytes_with_query(final_query, st.session_state.page_number)
    total_pages = result["total_pages"]
    articles = result["docs"]
    total_articles = result.get("total_docs", 0)  # Get total count of articles matching the query
    logger.info(f"Retrieved {len(articles)} articles for page {result['page_number']} of {total_pages} (Total: {total_articles})")

    # Show current filter status
    if final_query or selected_authors:
        logger.info("Displaying active filter information")
        filter_info = []
        
        # Show selected authors
        if selected_authors:
            authors_display = ", ".join(selected_authors) if len(selected_authors) <= 3 else f"{', '.join(selected_authors[:3])} +{len(selected_authors)-3} more"
            filter_info.append(f"✍️ Authors: {authors_display}")
        
        # Show other filters from final_query
        if final_query:
            if "summary_review_status" in final_query:
                status_display = {
                    "pending": "🟡 Pending",
                    "accepted": "🟢 Accepted",
                    "rejected": "🔴 Rejected"
                }.get(final_query["summary_review_status"], final_query["summary_review_status"])
                filter_info.append(f"📊 Summary Status: {status_display}")
            if "orgnl_artcl_rv_sts" in final_query:
                original_status_display = {
                    "pending": "🟡 Pending",
                    "accepted": "🟢 Accepted",
                    "rejected": "🔴 Rejected"
                }.get(final_query["orgnl_artcl_rv_sts"], final_query["orgnl_artcl_rv_sts"])
                filter_info.append(f"📄 Article Status: {original_status_display}")
            if "Best_byte" in final_query:
                best_byte_display = "✅ Yes" if final_query["Best_byte"] else "❌ No"
                filter_info.append(f"⭐ Best Byte: {best_byte_display}")
            if "Year" in final_query:
                filter_info.append(f"📅 Year: {final_query['Year']}")
            if "content_summary" in final_query:
                filter_info.append("📝 Has Summary: Yes")
            elif "$or" in final_query:
                filter_info.append("📝 Has Summary: No")
            if "pdf_name" in final_query:
                filter_info.append(f"📚 Edition: {final_query['pdf_name']}")
        
        if filter_info:
            # Add total articles count to the filter info
            filter_info.append(f"📊 Total: {total_articles} articles")
            st.info("🔍 **Active Filters:** " + " | ".join(filter_info))
            logger.info(f"Active filters displayed: {' | '.join(filter_info)}")
        else:
            # Even if no filters, show total count
            st.info(f"📊 **Total Articles:** {total_articles}")
            logger.info(f"Total articles displayed: {total_articles}")

    # Page info (centered)
    st.markdown(
        f"<div style='text-align:center; font-weight:bold;'>Page {result['page_number']} of {total_pages}</div>",
        unsafe_allow_html=True
    )
    logger.info(f"Displaying page {result['page_number']} of {total_pages}")

    # --- ARTICLES ---
    if articles:
        logger.info(f"Displaying {len(articles)} articles")
        for i, article in enumerate(articles):
            logger.debug(f"Processing article {i+1}: {article.get('Title', 'Untitled')[:50]}...")
            with st.container():
                st.markdown("---")
                st.subheader(f"📖 {article.get('Title', 'Untitled')}")
                
                # Current Title section with edit functionality
                article_id = article.get('_id')
                current_title = article.get('current_title', '')
                edit_title_key = f"edit_title_{article_id}"
                save_confirm_title_key = f"save_confirm_title_{article_id}"
                save_final_title_key = f"save_final_title_{article_id}"
                
                if st.session_state.get(edit_title_key, False):
                    # Edit mode for current title
                    logger.debug(f"Article {i+1} current title in edit mode")
                    edited_title = st.text_input(
                        "Edit Current Title:",
                        value=current_title,
                        key=f"title_edit_{article_id}",
                        help="Edit the current title. This will be displayed as the modified version of the original title."
                    )
                    
                    # Save and Cancel buttons for title
                    title_save_col, title_cancel_col = st.columns(2)
                    
                    with title_save_col:
                        if st.button("💾 Save Title", key=f"save_title_{article_id}", type="primary"):
                            logger.info(f"Save title button clicked for article {article_id}")
                            st.session_state[save_confirm_title_key] = True
                    
                    with title_cancel_col:
                        if st.button("❌ Cancel", key=f"cancel_title_{article_id}"):
                            logger.info(f"Cancel title edit for article {article_id}")
                            st.session_state[edit_title_key] = False
                            st.session_state[save_confirm_title_key] = False
                            st.session_state[save_final_title_key] = False
                            st.rerun()
                    
                    # First confirmation dialog for title
                    if st.session_state.get(save_confirm_title_key, False):
                        st.warning("⚠️ Are you sure you want to save changes to the current title?")
                        confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 1])
                        
                        with confirm_col1:
                            if st.button("✅ Yes, Save", key=f"yes_save_title_{article_id}", type="primary"):
                                logger.info(f"First confirmation for title save for article {article_id}")
                                st.session_state[save_confirm_title_key] = False
                                st.session_state[save_final_title_key] = True
                                st.rerun()
                        
                        with confirm_col2:
                            if st.button("❌ No, Cancel", key=f"no_save_title_{article_id}"):
                                logger.info(f"User cancelled title save for article {article_id}")
                                st.session_state[save_confirm_title_key] = False
                                st.rerun()
                    
                    # Second confirmation dialog for title
                    if st.session_state.get(save_final_title_key, False):
                        st.error("🚨 Final confirmation: This will permanently update the current title. Are you absolutely sure?")
                        final_col1, final_col2, final_col3 = st.columns([1, 1, 1])
                        
                        with final_col1:
                            if st.button("✅ YES, SAVE NOW", key=f"final_save_title_{article_id}", type="primary"):
                                logger.info(f"Final confirmation for title save for article {article_id}")
                                # Update MongoDB
                                try:
                                    collection.update_one(
                                        {"_id": article_id},
                                        {"$set": {"current_title": edited_title}}
                                    )
                                    st.success("✅ Current title updated successfully!")
                                    logger.info(f"Successfully updated current title for article {article_id}")
                                    # Reset edit state
                                    st.session_state[edit_title_key] = False
                                    st.session_state[save_final_title_key] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Failed to update title: {str(e)}")
                                    logger.error(f"Failed to update title for article {article_id}: {str(e)}")
                        
                        with final_col2:
                            if st.button("❌ Cancel", key=f"final_cancel_title_{article_id}"):
                                logger.info(f"User cancelled final title save for article {article_id}")
                                st.session_state[save_final_title_key] = False
                                st.rerun()
                else:
                    # View mode for current title
                    if current_title and current_title.strip():
                        st.markdown(f"📝 **Current Title:** {current_title}")
                        logger.debug(f"Article {i+1} current title displayed: {current_title}")
                    else:
                        st.markdown("📝 **Current Title:** *[Blank - No modified version yet]*")
                        logger.debug(f"Article {i+1} has no current title")
                    
                    # Edit button for title
                    if st.button("✏️ Edit Title", key=f"edit_title_btn_{article_id}"):
                        logger.info(f"Edit title button clicked for article {article_id}")
                        st.session_state[edit_title_key] = True
                        st.rerun()
                
                # Display Best Byte status
                best_byte_value = article.get('Best_byte', False)
                best_byte_display = "True" if best_byte_value else "False"
                st.markdown(f"⭐ **best_byte:** {best_byte_display}")
                logger.debug(f"Article {i+1} best_byte status: {best_byte_display}")
                
                st.markdown(f"✍️ **Author:** {article.get('Author', 'Unknown')}")
                st.markdown(f"🏷️ **Category:** {article.get('Category', '')} | {article.get('Subcategory', '')}")
                st.markdown(f"📝 **UUID:** {article.get('uuid', '')}")
                st.markdown(f"📄 **PDF:** {article.get('pdf_name', '')}")
                
                # Show chunk information if available
                if 'chunk_number' in article:
                    st.markdown(f"🔢 **Chunk:** {article['chunk_number']}")
                    logger.debug(f"Article {i+1} has chunk number: {article['chunk_number']}")
                
                # Show fragment information if available
                if article.get('is_fragment', False):
                    st.warning("⚠️ This article was extracted from a fragment")
                    if 'fragment_confidence' in article:
                        st.markdown(f"🎯 **Confidence:** {article['fragment_confidence']:.2f}")
                    logger.debug(f"Article {i+1} is a fragment with confidence: {article.get('fragment_confidence', 'N/A')}")
                
                # Create 2x2 grid layout for expanders
                col1, col2 = st.columns(2)
                
                # Left column - Original versions
                with col1:
                    # Show Content Summary if available
                    if article.get('content_summary'):
                        logger.debug(f"Article {i+1} has content summary, displaying review interface")
                        with st.expander("Content Summary", expanded=False):
                            st.markdown(article.get('content_summary', ''))
                            
                            # Show current review status
                            current_status = article.get('summary_review_status', 'pending')
                            status_color = {
                                'accepted': '🟢',
                                'rejected': '🔴', 
                                'pending': '🟡'
                            }.get(current_status, '🟡')
                            
                            st.markdown(f"**Current Status:** {status_color} {current_status.title()}")
                            logger.debug(f"Article {i+1} current status: {current_status}")
                            
                            # Accept/Reject buttons
                            btn_col1, btn_col2 = st.columns(2)
                            
                            with btn_col1:
                                if st.button("✅ Accept", key=f"accept_{article.get('_id')}", type="primary"):
                                    logger.info(f"Accept button clicked for article {article.get('_id')}")
                                    st.session_state[f"show_accept_confirm_{article.get('_id')}"] = True
                            
                            with btn_col2:
                                if st.button("❌ Reject", key=f"reject_{article.get('_id')}", type="secondary"):
                                    logger.info(f"Reject button clicked for article {article.get('_id')}")
                                    st.session_state[f"show_reject_confirm_{article.get('_id')}"] = True
                            
                            # Accept confirmation dialog
                            if st.session_state.get(f"show_accept_confirm_{article.get('_id')}", False):
                                logger.info(f"Showing accept confirmation dialog for article {article.get('_id')}")
                                st.warning("⚠️ Are you sure you want to accept this summary?")
                                confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 1])
                                
                                with confirm_col1:
                                    if st.button("✅ Yes, Accept", key=f"yes_accept_{article.get('_id')}", type="primary"):
                                        logger.info(f"User confirmed acceptance for article {article.get('_id')}")
                                        success = update_summary_review_status(str(article.get('_id')), "accepted")
                                        if success:
                                            st.success("✅ Summary accepted successfully!")
                                            logger.info(f"Successfully accepted article {article.get('_id')}")
                                            st.session_state[f"show_accept_confirm_{article.get('_id')}"] = False
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to update status. Please try again.")
                                            logger.error(f"Failed to accept article {article.get('_id')}")
                                
                                with confirm_col2:
                                    if st.button("❌ No, Cancel", key=f"no_accept_{article.get('_id')}"):
                                        logger.info(f"User cancelled acceptance for article {article.get('_id')}")
                                        st.session_state[f"show_accept_confirm_{article.get('_id')}"] = False
                                        st.rerun()
                            
                            # Reject confirmation dialog
                            if st.session_state.get(f"show_reject_confirm_{article.get('_id')}", False):
                                logger.info(f"Showing reject confirmation dialog for article {article.get('_id')}")
                                st.warning("⚠️ Are you sure you want to reject this summary?")
                                confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 1])
                                
                                with confirm_col1:
                                    if st.button("✅ Yes, Reject", key=f"yes_reject_{article.get('_id')}", type="primary"):
                                        logger.info(f"User confirmed rejection for article {article.get('_id')}")
                                        success = update_summary_review_status(str(article.get('_id')), "rejected")
                                        if success:
                                            st.success("❌ Summary rejected successfully!")
                                            logger.info(f"Successfully rejected article {article.get('_id')}")
                                            st.session_state[f"show_reject_confirm_{article.get('_id')}"] = False
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to update status. Please try again.")
                                            logger.error(f"Failed to reject article {article.get('_id')}")
                                
                                with confirm_col2:
                                    if st.button("❌ No, Cancel", key=f"no_reject_{article.get('_id')}"):
                                        logger.info(f"User cancelled rejection for article {article.get('_id')}")
                                        st.session_state[f"show_reject_confirm_{article.get('_id')}"] = False
                                        st.rerun()
                    
                    with st.expander("Original Content"):
                        st.write(article.get("Content", ""))
                        logger.debug(f"Article {i+1} content displayed")
                        
                        # Show current original article review status
                        current_article_status = article.get('orgnl_artcl_rv_sts', 'pending')
                        status_color = {
                            'accepted': '🟢',
                            'rejected': '🔴', 
                            'pending': '🟡'
                        }.get(current_article_status, '🟡')
                        
                        st.markdown(f"**Original Article Review Status:** {status_color} {current_article_status.title()}")
                        logger.debug(f"Article {i+1} original article review status: {current_article_status}")
                        
                        # Accept/Reject buttons for original article
                        btn_col1, btn_col2 = st.columns(2)
                        
                        with btn_col1:
                            if st.button("✅ Accept Article", key=f"accept_article_{article.get('_id')}", type="primary"):
                                logger.info(f"Accept article button clicked for article {article.get('_id')}")
                                st.session_state[f"show_accept_article_confirm_{article.get('_id')}"] = True
                        
                        with btn_col2:
                            if st.button("❌ Reject Article", key=f"reject_article_{article.get('_id')}", type="secondary"):
                                logger.info(f"Reject article button clicked for article {article.get('_id')}")
                                st.session_state[f"show_reject_article_confirm_{article.get('_id')}"] = True
                        
                        # Accept article confirmation dialog
                        if st.session_state.get(f"show_accept_article_confirm_{article.get('_id')}", False):
                            logger.info(f"Showing accept article confirmation dialog for article {article.get('_id')}")
                            st.warning("⚠️ Are you sure you want to accept this original article?")
                            confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 1])
                            
                            with confirm_col1:
                                if st.button("✅ Yes, Accept", key=f"yes_accept_article_{article.get('_id')}", type="primary"):
                                    logger.info(f"User confirmed article acceptance for article {article.get('_id')}")
                                    success = update_original_article_review_status(str(article.get('_id')), "accepted")
                                    if success:
                                        st.success("✅ Original article accepted successfully!")
                                        logger.info(f"Successfully accepted original article {article.get('_id')}")
                                        st.session_state[f"show_accept_article_confirm_{article.get('_id')}"] = False
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to update article status. Please try again.")
                                        logger.error(f"Failed to accept original article {article.get('_id')}")
                            
                            with confirm_col2:
                                if st.button("❌ No, Cancel", key=f"no_accept_article_{article.get('_id')}"):
                                    logger.info(f"User cancelled article acceptance for article {article.get('_id')}")
                                    st.session_state[f"show_accept_article_confirm_{article.get('_id')}"] = False
                                    st.rerun()
                        
                        # Reject article confirmation dialog
                        if st.session_state.get(f"show_reject_article_confirm_{article.get('_id')}", False):
                            logger.info(f"Showing reject article confirmation dialog for article {article.get('_id')}")
                            st.warning("⚠️ Are you sure you want to reject this original article?")
                            confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 1])
                            
                            with confirm_col1:
                                if st.button("✅ Yes, Reject", key=f"yes_reject_article_{article.get('_id')}", type="primary"):
                                    logger.info(f"User confirmed article rejection for article {article.get('_id')}")
                                    success = update_original_article_review_status(str(article.get('_id')), "rejected")
                                    if success:
                                        st.success("❌ Original article rejected successfully!")
                                        logger.info(f"Successfully rejected original article {article.get('_id')}")
                                        st.session_state[f"show_reject_article_confirm_{article.get('_id')}"] = False
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to update article status. Please try again.")
                                        logger.error(f"Failed to reject original article {article.get('_id')}")
                            
                            with confirm_col2:
                                if st.button("❌ No, Cancel", key=f"no_reject_article_{article.get('_id')}"):
                                    logger.info(f"User cancelled article rejection for article {article.get('_id')}")
                                    st.session_state[f"show_reject_article_confirm_{article.get('_id')}"] = False
                                    st.rerun()
                
                # Right column - Current/Modified versions
                with col2:
                    # Current Content Summary expander
                    with st.expander("Current Content Summary", expanded=False):
                        current_summary = article.get('current_summary', '')
                        article_id = article.get('_id')
                        
                        # Check if we're in edit mode for this article's summary
                        edit_key = f"edit_summary_{article_id}"
                        save_confirm_key = f"save_confirm_summary_{article_id}"
                        save_final_key = f"save_final_summary_{article_id}"
                        
                        if st.session_state.get(edit_key, False):
                            # Edit mode - show text area with markdown formatting visible
                            logger.debug(f"Article {i+1} summary in edit mode")
                            edited_summary = st.text_area(
                                "Edit Content Summary (Markdown formatting visible):",
                                value=current_summary,
                                height=200,
                                key=f"summary_edit_{article_id}",
                                help="Edit the content summary. Markdown formatting like ##, **, etc. will be visible as text."
                            )
                            
                            # Save and Cancel buttons
                            save_col, cancel_col = st.columns(2)
                            
                            with save_col:
                                if st.button("💾 Save Changes", key=f"save_summary_{article_id}", type="primary"):
                                    logger.info(f"Save summary button clicked for article {article_id}")
                                    st.session_state[save_confirm_key] = True
                            
                            with cancel_col:
                                if st.button("❌ Cancel", key=f"cancel_summary_{article_id}"):
                                    logger.info(f"Cancel summary edit for article {article_id}")
                                    st.session_state[edit_key] = False
                                    st.session_state[save_confirm_key] = False
                                    st.session_state[save_final_key] = False
                                    st.rerun()
                            
                            # First confirmation dialog
                            if st.session_state.get(save_confirm_key, False):
                                st.warning("⚠️ Are you sure you want to save changes to the content summary?")
                                confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 1])
                                
                                with confirm_col1:
                                    if st.button("✅ Yes, Save", key=f"yes_save_summary_{article_id}", type="primary"):
                                        logger.info(f"First confirmation for summary save for article {article_id}")
                                        st.session_state[save_confirm_key] = False
                                        st.session_state[save_final_key] = True
                                        st.rerun()
                                
                                with confirm_col2:
                                    if st.button("❌ No, Cancel", key=f"no_save_summary_{article_id}"):
                                        logger.info(f"User cancelled summary save for article {article_id}")
                                        st.session_state[save_confirm_key] = False
                                        st.rerun()
                            
                            # Second confirmation dialog
                            if st.session_state.get(save_final_key, False):
                                st.error("🚨 Final confirmation: This will permanently update the content summary. Are you absolutely sure?")
                                final_col1, final_col2, final_col3 = st.columns([1, 1, 1])
                                
                                with final_col1:
                                    if st.button("✅ YES, SAVE NOW", key=f"final_save_summary_{article_id}", type="primary"):
                                        logger.info(f"Final confirmation for summary save for article {article_id}")
                                        # Update MongoDB
                                        try:
                                            collection.update_one(
                                                {"_id": article_id},
                                                {"$set": {"current_summary": edited_summary}}
                                            )
                                            st.success("✅ Content summary updated successfully!")
                                            logger.info(f"Successfully updated summary for article {article_id}")
                                            # Reset edit state
                                            st.session_state[edit_key] = False
                                            st.session_state[save_final_key] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Failed to update summary: {str(e)}")
                                            logger.error(f"Failed to update summary for article {article_id}: {str(e)}")
                                
                                with final_col2:
                                    if st.button("❌ Cancel", key=f"final_cancel_summary_{article_id}"):
                                        logger.info(f"User cancelled final summary save for article {article_id}")
                                        st.session_state[save_final_key] = False
                                        st.rerun()
                        else:
                            # View mode
                            if current_summary and current_summary.strip():
                                st.markdown(current_summary)
                                logger.debug(f"Article {i+1} current summary displayed")
                            else:
                                st.info("No modified version yet")
                                logger.debug(f"Article {i+1} has no current summary")
                            
                            # Edit button
                            if st.button("✏️ Edit", key=f"edit_summary_btn_{article_id}"):
                                logger.info(f"Edit summary button clicked for article {article_id}")
                                st.session_state[edit_key] = True
                                st.rerun()
                    
                    # Current Original Article expander
                    with st.expander("Current Original Article", expanded=False):
                        current_original_article = article.get('current_origina_article', '')
                        article_id = article.get('_id')
                        
                        # Check if we're in edit mode for this article's original content
                        edit_key = f"edit_article_{article_id}"
                        save_confirm_key = f"save_confirm_article_{article_id}"
                        save_final_key = f"save_final_article_{article_id}"
                        
                        if st.session_state.get(edit_key, False):
                            # Edit mode - show text area with markdown formatting visible
                            logger.debug(f"Article {i+1} original article in edit mode")
                            edited_article = st.text_area(
                                "Edit Original Article (Markdown formatting visible):",
                                value=current_original_article,
                                height=300,
                                key=f"article_edit_{article_id}",
                                help="Edit the original article content. Markdown formatting like ##, **, etc. will be visible as text."
                            )
                            
                            # Save and Cancel buttons
                            save_col, cancel_col = st.columns(2)
                            
                            with save_col:
                                if st.button("💾 Save Changes", key=f"save_article_{article_id}", type="primary"):
                                    logger.info(f"Save article button clicked for article {article_id}")
                                    st.session_state[save_confirm_key] = True
                            
                            with cancel_col:
                                if st.button("❌ Cancel", key=f"cancel_article_{article_id}"):
                                    logger.info(f"Cancel article edit for article {article_id}")
                                    st.session_state[edit_key] = False
                                    st.session_state[save_confirm_key] = False
                                    st.session_state[save_final_key] = False
                                    st.rerun()
                            
                            # First confirmation dialog
                            if st.session_state.get(save_confirm_key, False):
                                st.warning("⚠️ Are you sure you want to save changes to the original article?")
                                confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 1])
                                
                                with confirm_col1:
                                    if st.button("✅ Yes, Save", key=f"yes_save_article_{article_id}", type="primary"):
                                        logger.info(f"First confirmation for article save for article {article_id}")
                                        st.session_state[save_confirm_key] = False
                                        st.session_state[save_final_key] = True
                                        st.rerun()
                                
                                with confirm_col2:
                                    if st.button("❌ No, Cancel", key=f"no_save_article_{article_id}"):
                                        logger.info(f"User cancelled article save for article {article_id}")
                                        st.session_state[save_confirm_key] = False
                                        st.rerun()
                            
                            # Second confirmation dialog
                            if st.session_state.get(save_final_key, False):
                                st.error("🚨 Final confirmation: This will permanently update the original article. Are you absolutely sure?")
                                final_col1, final_col2, final_col3 = st.columns([1, 1, 1])
                                
                                with final_col1:
                                    if st.button("✅ YES, SAVE NOW", key=f"final_save_article_{article_id}", type="primary"):
                                        logger.info(f"Final confirmation for article save for article {article_id}")
                                        # Update MongoDB
                                        try:
                                            collection.update_one(
                                                {"_id": article_id},
                                                {"$set": {"current_origina_article": edited_article}}
                                            )
                                            st.success("✅ Original article updated successfully!")
                                            logger.info(f"Successfully updated original article for article {article_id}")
                                            # Reset edit state
                                            st.session_state[edit_key] = False
                                            st.session_state[save_final_key] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Failed to update article: {str(e)}")
                                            logger.error(f"Failed to update article for article {article_id}: {str(e)}")
                                
                                with final_col2:
                                    if st.button("❌ Cancel", key=f"final_cancel_article_{article_id}"):
                                        logger.info(f"User cancelled final article save for article {article_id}")
                                        st.session_state[save_final_key] = False
                                        st.rerun()
                        else:
                            # View mode
                            if current_original_article and current_original_article.strip():
                                st.write(current_original_article)
                                logger.debug(f"Article {i+1} current original article displayed")
                            else:
                                st.info("No modified version yet")
                                logger.debug(f"Article {i+1} has no current original article")
                            
                            # Edit button
                            if st.button("✏️ Edit", key=f"edit_article_btn_{article_id}"):
                                logger.info(f"Edit article button clicked for article {article_id}")
                                st.session_state[edit_key] = True
                                st.rerun()
                
                # Show LLM Review if article has been reviewed
                if article.get('reviewed_by_llm') == 1 and article.get('llm_review'):
                    logger.debug(f"Article {i+1} has LLM review, displaying review results")
                    with st.expander("🤖 LLM Review Results"):
                        llm_review = article.get('llm_review', {})
                        
                        st.markdown(f"**Problem Identification:** {llm_review.get('describes_specific_problem', 'N/A')}")
                        st.markdown(f"**Explanation:** {llm_review.get('problem_explanation', 'N/A')}")
                        
                        st.markdown(f"**Actionable Insights:** {llm_review.get('provides_actionable_insights', 'N/A')}")
                        st.markdown(f"**Explanation:** {llm_review.get('insights_explanation', 'N/A')}")
                        
                        st.markdown(f"**Writing Style (No First Person):** {llm_review.get('avoids_first_person', 'N/A')}")
                        st.markdown(f"**Explanation:** {llm_review.get('writing_style_explanation', 'N/A')}")
                        
                        st.markdown(f"**Length Appropriate:** {llm_review.get('length_appropriate', 'N/A')}")
                        st.markdown(f"**Word Count:** {llm_review.get('actual_word_count', 'N/A')} words")
                        
                        st.markdown(f"**Recommendations:** {llm_review.get('recommendations', 'N/A')}")
    else:
        logger.warning("No articles found matching the current filters")
        st.warning("No articles found in the database.")

    # --- NAVIGATION (BOTTOM) ---
    logger.info("Setting up bottom navigation")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅ Previous", key="prev_bottom") and st.session_state.page_number > 1:
            logger.info(f"Bottom Previous button clicked, changing page from {st.session_state.page_number} to {st.session_state.page_number - 1}")
            st.session_state.page_number -= 1
    with col3:
        if st.button("Next ➡", key="next_bottom") and st.session_state.page_number < total_pages:
            logger.info(f"Bottom Next button clicked, changing page from {st.session_state.page_number} to {st.session_state.page_number + 1}")
            st.session_state.page_number += 1
    
    logger.info("View Extracted Articles page rendering completed")

