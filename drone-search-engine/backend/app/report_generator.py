"""
Site Intelligence Report Generator
- K-means clusters images by visual themes
- Groq API (LLaMA 3.3 70B) generates written analysis
- ReportLab exports as professional PDF
"""

import os
import json
from datetime import datetime
from typing import List, Dict
from collections import Counter


def _cluster_images(images: List[Dict], n_clusters: int = 5) -> List[Dict]:
    """
    Cluster processed images by their detected objects and captions
    to find dominant visual themes in the collection.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans

    # Build text representation for each image
    texts = []
    for img in images:
        parts = []
        if img.get("caption"):
            parts.append(img["caption"])
        objs = img.get("detected_objects", [])
        if isinstance(objs, list):
            parts.append(" ".join(objs))
        if img.get("ocr_text"):
            parts.append(img["ocr_text"])
        texts.append(" ".join(parts) if parts else "aerial image")

    # TF-IDF vectorize
    vectorizer = TfidfVectorizer(max_features=200, stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Adjust clusters to data size
    actual_k = min(n_clusters, len(images))
    if actual_k < 2:
        return [{
            "cluster_id": 0,
            "size": len(images),
            "summary": texts[0] if texts else "aerial imagery",
            "top_objects": [],
            "image_ids": [img["image_id"] for img in images]
        }]

    kmeans = KMeans(n_clusters=actual_k, n_init=10, random_state=42)
    labels = kmeans.fit_predict(tfidf_matrix)

    clusters = []
    for i in range(actual_k):
        cluster_indices = [j for j, l in enumerate(labels) if l == i]
        cluster_images = [images[j] for j in cluster_indices]

        # Find top objects in cluster
        all_objects = []
        for img in cluster_images:
            objs = img.get("detected_objects", [])
            if isinstance(objs, list):
                all_objects.extend(objs)
        top_objects = [obj for obj, _ in Counter(all_objects).most_common(5)]

        # Representative captions
        captions = [img.get("caption", "") for img in cluster_images if img.get("caption")]

        clusters.append({
            "cluster_id": i,
            "size": len(cluster_images),
            "captions": captions[:5],
            "top_objects": top_objects,
            "image_ids": [img["image_id"] for img in cluster_images],
        })

    return clusters


def generate_site_report(images: List[Dict]) -> Dict:
    """
    Generate a Site Intelligence Report using Groq API (LLaMA 3.3 70B).
    Mirrors Skylark Spectra's site reporting style.
    """
    from groq import Groq

    # Cluster images
    clusters = _cluster_images(images)

    # Build object frequency summary
    all_objects = []
    all_colors = []
    for img in images:
        objs = img.get("detected_objects", [])
        if isinstance(objs, list):
            all_objects.extend(objs)
        cols = img.get("dominant_colors", [])
        if isinstance(cols, list):
            all_colors.extend(cols)

    object_freq = dict(Counter(all_objects).most_common(15))
    color_freq = dict(Counter(all_colors).most_common(10))

    # Build cluster summaries for the prompt
    cluster_text = ""
    for c in clusters:
        cluster_text += f"\nCluster {c['cluster_id'] + 1} ({c['size']} images):\n"
        cluster_text += f"  Top objects: {', '.join(c['top_objects']) if c['top_objects'] else 'N/A'}\n"
        cluster_text += f"  Sample captions: {'; '.join(c['captions'][:3])}\n"

    prompt = f"""You are a drone site intelligence analyst. Generate a professional Site Intelligence Report based on this aerial image collection analysis.

Collection Stats:
- Total images analyzed: {len(images)}
- Visual theme clusters identified: {len(clusters)}
- Analysis date: {datetime.now().strftime('%B %d, %Y')}

Cluster Analysis:
{cluster_text}

Object Detection Summary (object: count):
{json.dumps(object_freq, indent=2)}

Dominant Color Palette:
{json.dumps(color_freq, indent=2)}

Generate a report with these exact sections:
1. EXECUTIVE SUMMARY — 3-4 sentence overview of the site
2. SCENE BREAKDOWN — describe each cluster as a distinct site zone/area
3. OBJECT ANALYSIS — what dominant objects tell us about site activity
4. COLOR & TERRAIN ANALYSIS — what the color palette reveals about terrain/conditions
5. AREAS OF INTEREST — flag anything unusual or noteworthy for site managers
6. RECOMMENDATIONS — 3 actionable next steps based on the analysis

Write professionally. Be specific. Reference actual data from the clusters and object counts."""

    # Groq API call
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables. Add it to your .env file.")

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    report_content = response.choices[0].message.content

    return {
        "title": "Site Intelligence Report",
        "subtitle": f"Aerial Image Collection Analysis — {datetime.now().strftime('%B %d, %Y')}",
        "content": report_content,
        "image_count": len(images),
        "cluster_count": len(clusters),
        "clusters": clusters,
        "object_frequencies": object_freq,
        "color_palette": list(color_freq.keys()),
        "generated_at": datetime.now().isoformat(),
    }


def export_report_pdf(report: Dict, output_dir: str) -> str:
    """Export the report as a professional PDF using ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER

    # If report_data is nested (from DB retrieval), extract it
    if "report_data" in report and isinstance(report["report_data"], dict):
        report = report["report_data"]

    pdf_filename = f"site_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=HexColor("#1a1a2e"),
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=HexColor("#6b7280"),
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=HexColor("#0f172a"),
        spaceBefore=16,
        spaceAfter=8,
        borderWidth=0,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=HexColor("#374151"),
        spaceAfter=8,
    )

    # Build PDF content
    elements = []

    # Header
    elements.append(Paragraph("Insights", ParagraphStyle(
        "Brand", parent=styles["Normal"], fontSize=9,
        textColor=HexColor("#6366f1"), alignment=TA_CENTER, spaceAfter=4
    )))
    elements.append(Paragraph(
        report.get("title", "Site Intelligence Report"), title_style
    ))
    elements.append(Paragraph(
        report.get("subtitle", f"Generated {datetime.now().strftime('%B %d, %Y')}"),
        subtitle_style
    ))

    # Divider
    elements.append(HRFlowable(
        width="100%", thickness=1, color=HexColor("#e5e7eb"), spaceAfter=16
    ))

    # Stats bar
    stats_data = [[
        f"Images Analyzed: {report.get('image_count', 0)}",
        f"Clusters: {report.get('cluster_count', 0)}",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
    ]]
    stats_table = Table(stats_data, colWidths=[180, 120, 180])
    stats_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#475569")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 16))

    # Main report content — split by sections
    content = report.get("content", "")
    paragraphs = content.split("\n")

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Detect section headers
        if para.startswith("#") or para.isupper() or any(
            para.startswith(f"{i}.") for i in range(1, 10)
        ):
            clean = para.lstrip("#").lstrip("0123456789.").strip()
            clean = clean.replace("**", "")
            elements.append(Paragraph(clean, section_style))
        else:
            # Clean markdown bold
            clean = para.replace("**", "").replace("*", "")
            elements.append(Paragraph(clean, body_style))

    # Color palette section
    colors = report.get("color_palette", [])
    if colors:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("DOMINANT COLOR PALETTE", section_style))

        color_cells = []
        for color in colors[:8]:
            try:
                color_cells.append(color)
            except Exception:
                pass

        if color_cells:
            swatch_data = [color_cells[:4]]
            swatch_table = Table(swatch_data, colWidths=[80] * min(4, len(color_cells)))
            swatch_style = [
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#ffffff")),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
            for idx, color in enumerate(color_cells[:4]):
                try:
                    swatch_style.append(
                        ("BACKGROUND", (idx, 0), (idx, 0), HexColor(color))
                    )
                except Exception:
                    pass
            swatch_table.setStyle(TableStyle(swatch_style))
            elements.append(swatch_table)

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=HexColor("#d1d5db"), spaceAfter=8
    ))
    elements.append(Paragraph(
        f"Generated by Drone Image Semantic Search Engine ·  {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7,
                       textColor=HexColor("#9ca3af"), alignment=TA_CENTER)
    ))

    doc.build(elements)
    return pdf_path