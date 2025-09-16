import streamlit as st
import sys
import os
from pathlib import Path

# Add current directory to Python path to find modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from byte_extractor_service import (
    collection, get_paginated_bytes_with_query, update_summary_review_status, update_original_article_review_status
)
from logger_config import logger

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
    col1, col2, col3 = st.columns(3)
    with col1:
        summary_status_filter = st.selectbox(
            "📊 Summary Review Status:",
            ["All", "🟡 Pending", "🟢 Accepted", "🔴 Rejected"],
            help="Filter articles by their summary review status"
        )
        logger.info(f"Summary status filter selected: {summary_status_filter}")
    
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
    
    # Second dropdown: Have Summary (based on selected year)
    if selected_year != "All Years":
        logger.info(f"Processing summary filter for year: {selected_year}")
        # Filter documents by selected year
        year_query = {"Year": selected_year}
        logger.debug(f"Year query: {year_query}")
        year_docs = list(collection.find(year_query, {"content_summary": 1, "pdf_name": 1}))
        logger.info(f"Found {len(year_docs)} documents for year {selected_year}")
        
        # Count documents with and without content_summary
        has_summary_count = sum(1 for doc in year_docs if doc.get('content_summary'))
        no_summary_count = len(year_docs) - has_summary_count
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
            st.warning(f"No articles found for year {selected_year}")
            logger.warning(f"No articles found for year {selected_year}")
    else:
        selected_summary = "All"
        logger.info("No year selected, summary filter set to 'All'")
    
    # Third dropdown: Available Editions (based on year and summary selection)
    if selected_year != "All Years" and selected_summary != "All":
        logger.info(f"Processing PDF selection for year: {selected_year}, summary: {selected_summary}")
        # Determine if we want articles with or without summary
        want_summary = selected_summary.startswith("✅")
        logger.info(f"Want summary: {want_summary}")
        
        # Build query based on selections
        query = {"Year": selected_year}
        if want_summary:
            query["content_summary"] = {"$exists": True, "$ne": ""}
        else:
            query["$or"] = [
                {"content_summary": {"$exists": False}},
                {"content_summary": ""},
                {"content_summary": None}
            ]
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
        logger.info("Using fallback PDF selection (no year/summary filters)")
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
    
    # Apply summary filter
    if selected_year != "All Years" and selected_summary != "All":
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
    
    if summary_conditions:
        if len(summary_conditions) == 1:
            and_conditions.append(summary_conditions[0])
            logger.debug("Added single summary condition")
        else:
            and_conditions.append({"$or": summary_conditions})
            logger.debug(f"Added $or summary conditions: {len(summary_conditions)} conditions")
    
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
                filter_info.append(f"📊 Status: {status_display}")
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
                
                # Show Content Summary if available
                if article.get('content_summary'):
                    logger.debug(f"Article {i+1} has content summary, displaying review interface")
                    with st.expander("Content Summary", expanded=True):
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
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✅ Accept", key=f"accept_{article.get('_id')}", type="primary"):
                                logger.info(f"Accept button clicked for article {article.get('_id')}")
                                st.session_state[f"show_accept_confirm_{article.get('_id')}"] = True
                        
                        with col2:
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
                
                with st.expander("Read Content"):
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
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("✅ Accept Article", key=f"accept_article_{article.get('_id')}", type="primary"):
                            logger.info(f"Accept article button clicked for article {article.get('_id')}")
                            st.session_state[f"show_accept_article_confirm_{article.get('_id')}"] = True
                    
                    with col2:
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

