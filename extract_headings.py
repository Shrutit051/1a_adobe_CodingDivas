import fitz  # PyMuPDF
import re
from statistics import median
import os

class PDFHeadingExtractor:
    def __init__(self):
        pass

    def is_decorative(self, text):
        return (
            re.fullmatch(r"[.\-_\s]{5,}", text) or
            len(set(text.strip())) == 1 or
            len(text.strip()) < 3 or
            sum(c.isalpha() for c in text) < 3
        )

    def parse_pdf_spans(self, doc):
        all_spans = []
        for page_num, page in enumerate(doc, start=1):
            page_height = page.rect.height
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" not in block:
                    continue
                prev_line_text = None
                for line in block["lines"]:
                    # Gather all spans in the line
                    line_spans = []
                    bold_count = 0
                    total_count = 0
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text or self.is_decorative(text):
                            continue
                        y = span["bbox"][1]
                        x = span["bbox"][0]
                        if y < 0.05 * page_height or y > 0.95 * page_height:
                            continue
                        is_bold = "Bold" in span["font"]
                        if is_bold:
                            bold_count += 1
                        total_count += 1
                        entry = {
                            "text": text,
                            "size": round(span["size"], 1),
                            "font": span["font"],
                            "page": page_num,
                            "is_bold": is_bold,
                            "y": y,
                            "x": x
                        }
                        line_spans.append(entry)
                    # Only consider as heading if all spans are bold or only one bold span in the line
                    if line_spans:
                        is_single_bold = (bold_count == 1 and total_count == 1)
                        is_all_bold = (bold_count == total_count)
                        allow_heading = True
                        line_text = " ".join(span["text"] for span in line["spans"]).strip() if line["spans"] else ""
                        # Improved heuristics for headings
                        if is_all_bold:
                            # Must be at least 3 words or 15 characters
                            if len(line_text.split()) < 3 and len(line_text) < 15:
                                allow_heading = False
                            # Must start with uppercase
                            elif line_text and not line_text[0].isupper():
                                allow_heading = False
                            # Previous line should not end with hyphen
                            elif prev_line_text and prev_line_text.strip().endswith("-"):
                                allow_heading = False
                        if is_single_bold:
                            # Check if previous line ends with sentence-ending punctuation
                            if prev_line_text and prev_line_text.strip()[-1:] in ".:;!?":
                                allow_heading = False
                        if (is_all_bold or is_single_bold) and allow_heading:
                            all_spans.extend(line_spans)
                    # Update prev_line_text for next iteration
                    prev_line_text = " ".join(span["text"] for span in line["spans"]).strip() if line["spans"] else None
        return all_spans

    def adjust_font_sizes(self, spans):
        for span in spans:
            adjusted_size = span["size"] + (4 if span["is_bold"] else 0)
            span["adjusted_size"] = round(adjusted_size, 2)
        return spans

    def infer_dynamic_thresholds(self, spans):
        if not spans:
            return 50, 20, 10

        x_vals = [s["x"] for s in spans]
        base_x = min(x_vals) if x_vals else 50

        indent_gaps = [x - base_x for x in x_vals if (x - base_x) > 0]
        indent_delta = median(indent_gaps) if indent_gaps else 20

        y_deltas = []
        for i in range(1, len(spans)):
            a, b = spans[i - 1], spans[i]
            if a["adjusted_size"] == b["adjusted_size"] and a["page"] == b["page"]:
                y_deltas.append(abs(b["y"] - a["y"]))
        y_merge_threshold = median(y_deltas) if y_deltas else 15

        return base_x, indent_delta, y_merge_threshold


    def map_sizes_to_levels(self, spans):
        sizes = [s["adjusted_size"] for s in spans]
        unique = sorted(set(sizes), reverse=True)
        size_to_level = {}

        levels = ["H1", "H2", "H3"]
        for i, level in enumerate(levels):
            if i < len(unique):
                size_to_level[unique[i]] = level

        return size_to_level

    def build_outline(self, spans, size_to_level, base_x, indent_delta, y_merge_threshold):
        outline = []
        title_parts = []
        skip = set()

        for i, span in enumerate(spans):
            if i in skip:
                continue

            size = span["adjusted_size"]
            page = span["page"]
            x = span["x"]
            y = span["y"]
            text = span["text"]
            level = size_to_level.get(size)

            if not level and span["is_bold"]:
                same_page_spans = [s["x"] for s in spans if s["page"] == page and s["adjusted_size"] == size]
                baseline_x = min(same_page_spans) if same_page_spans else base_x
                if x - baseline_x >= indent_delta:
                    level = "H2"

            if not level:
                continue

            combined_text = text
            j = i + 1
            while j < len(spans):
                next_span = spans[j]
                if (
                    next_span["page"] == page
                    and next_span["adjusted_size"] == size
                    and abs(next_span["y"] - y) < 10
                    and abs(next_span["x"] - x) < 5
                    and next_span["font"] == span["font"]
                ):
                    combined_text += " " + next_span["text"]
                    skip.add(j)
                    y = next_span["y"]
                    j += 1
                else:
                    break

            if page == 1 and level == "H1" and not title_parts:
                title_parts.append(combined_text)

            outline.append({
                "level": level,
                "text": combined_text.strip(),
                "page": page,
                "y": y  # Store for section slicing
            })

        return title_parts, outline

    def find_heading_y(self, page, heading_text):
        """Find the vertical Y-position of the heading on a page."""
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            for line in block.get("lines", []):
                full_line = " ".join(span["text"] for span in line["spans"]).strip()
                if heading_text in full_line:
                    return line["bbox"][1]
        return 0

    def extract_section_texts(self, doc, outline):
        section_texts = {}
        heading_positions = []

        # Collect positions for each heading
        for item in outline:
            page_idx = item["page"] - 1
            y = item.get("y") or self.find_heading_y(doc[page_idx], item["text"])
            heading_positions.append((page_idx, y, item["text"]))

        # Extract section text between headings
        for idx, (start_page, start_y, heading_text) in enumerate(heading_positions):
            end_page, end_y = len(doc) - 1, float('inf')
            if idx + 1 < len(heading_positions):
                end_page, end_y, _ = heading_positions[idx + 1]

            section_lines = []

            for p in range(start_page, end_page + 1):
                page = doc[p]
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        y = line["bbox"][1]
                        if (p == start_page and y < start_y) or (p == end_page and y >= end_y):
                            continue
                        line_text = " ".join(span["text"] for span in line["spans"]).strip()
                        if line_text == heading_text:
                            continue
                        if line_text:
                            section_lines.append(line_text)

            section_texts[idx] = "\n".join(section_lines).strip()

        return section_texts

    def extract_toc(self, doc, max_pages=5):
        toc_entries = []
        toc_pattern = re.compile(r"(.+?)\.{2,}\s*(\d+)$")
        for page_num in range(min(max_pages, len(doc))):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    line_text = " ".join(span["text"] for span in line["spans"]).strip()
                    match = toc_pattern.match(line_text)
                    if match:
                        title, page_str = match.groups()
                        try:
                            page_number = int(page_str)
                            toc_entries.append({"title": title.strip(), "page": page_number})
                        except ValueError:
                            continue
        return toc_entries

    def extract_structured_headings(self, pdf_path, include_text=False):
        doc = fitz.open(pdf_path)
        spans = self.parse_pdf_spans(doc)
        spans = self.adjust_font_sizes(spans)
        base_x, indent_delta, y_merge_threshold = self.infer_dynamic_thresholds(spans)
        size_to_level = self.map_sizes_to_levels(spans)
        title_parts, outline = self.build_outline(spans, size_to_level, base_x, indent_delta, y_merge_threshold)

        toc = self.extract_toc(doc)

        # Use metadata title if no H1 heading found
        title = " ".join(title_parts).strip()
        if not title:
            meta_title = doc.metadata.get("title")
            if meta_title:
                title = meta_title.strip()
        # If still no title, use largest text on page 1
        if not title:
            page1_spans = [s for s in spans if s["page"] == 1]
            if page1_spans:
                max_size = max(s["adjusted_size"] for s in page1_spans)
                largest_spans = [s for s in page1_spans if s["adjusted_size"] == max_size]
                # Combine all largest text spans on page 1
                title = " ".join(s["text"] for s in largest_spans).strip()
        # If still no title, use filename without extension
        if not title:
            title = os.path.splitext(os.path.basename(pdf_path))[0]

        outline = [h for h in outline if h["text"].strip().lower() != title.strip().lower()]

        result = {
            "title": title,
            "outline": outline,
            # "toc": toc
        }

        if include_text:
            section_texts = self.extract_section_texts(doc, outline)
            for i, item in enumerate(outline):
                item["text_content"] = section_texts.get(i, "")

        for item in result["outline"]:
            item.pop("y", None)
        return result