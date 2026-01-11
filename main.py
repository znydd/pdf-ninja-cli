import argparse
import os
from pypdf import PdfReader, PdfWriter


def split_pdf(file_path, start_page, end_page, output_name):
    """
    Splits a PDF from start_page to end_page and saves it as output_name in the same folder.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    try:
        reader = PdfReader(file_path)
        writer = PdfWriter()

        # pypdf uses 0-indexed page numbers
        # The user provides 1-indexed page numbers
        total_pages = len(reader.pages)
        
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            print(f"Error: Invalid page range. Total pages: {total_pages}")
            return

        for i in range(start_page - 1, end_page):
            writer.add_page(reader.pages[i])

        output_dir = os.path.dirname(os.path.abspath(file_path))
        output_path = os.path.join(output_dir, output_name)

        with open(output_path, "wb") as f:
            writer.write(f)

        print(f"Successfully saved split PDF to: {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(description="PDF Ninja CLI - Split PDF files easily.")
    parser.add_argument("file_path", help="Path to the PDF file")
    parser.add_argument("start_page", type=int, help="Start page number (1-indexed)")
    parser.add_argument("end_page", type=int, help="End page number (1-indexed)")
    parser.add_argument("output_name", help="New PDF file name (e.g., split.pdf)")

    args = parser.parse_args()

    # Ensure output_name has .pdf extension if not provided
    output_name = args.output_name
    if not output_name.lower().endswith(".pdf"):
        output_name += ".pdf"

    split_pdf(args.file_path, args.start_page, args.end_page, output_name)


if __name__ == "__main__":
    main()
