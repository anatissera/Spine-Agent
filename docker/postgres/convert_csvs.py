"""
Convert AdventureWorks Microsoft CSV format to proper TSV for PostgreSQL COPY.

Microsoft format:
  - Field separator:  +|
  - Row terminator:   &|  followed by a newline
  - Fields with XML or long text can span multiple lines — so rows must be
    split on &|\\n, NOT on \\n alone.

Target format: tab-separated, fields with " or \\t quoted per RFC 4180.
"""
import csv
import io
import os
import re

# Tables with binary (varbinary) columns whose CSV content can't be safely
# converted. These are NOT part of the SpineAgent spine. We truncate them to
# empty files so the COPY loads 0 rows instead of crashing and aborting the
# rest of the install.sql transaction.
# Tables that fail CSV conversion due to binary blobs, XML, or encoding quirks.
# None of these are part of the SpineAgent spine (SalesOrder → Product → Person).
# We truncate them so COPY loads 0 rows and the init continues cleanly.
SKIP_TABLES = {
    "Document.csv",             # Production.Document — OLE2 .doc binaries
    "ProductPhoto.csv",         # Production.ProductPhoto — image binaries
    "ProductDescription.csv",   # Production.ProductDescription — format edge case row 97
    "Illustration.csv",         # Production.Illustration — large XML blobs
}


def convert_file(path: str) -> bool:
    """Convert file if it uses +| format. Returns True if converted, False if skipped."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        sample = f.read(1024)
        f.seek(0)
        content = f.read()

    # If no +| separator in the first 1 KB, file is already TSV — skip it
    if "+|" not in sample:
        return False

    output = io.StringIO()
    writer = csv.writer(
        output,
        delimiter="\t",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )

    # Split on the &| record terminator (supports multi-line XML/text fields).
    # Each element after split is one complete record (minus the &| terminator).
    records = re.split(r"&\|\r?\n", content)

    for record in records:
        # Strip any trailing &| on the very last record (no trailing newline)
        if record.endswith("&|"):
            record = record[:-2]
        record = record.strip()
        if not record:
            continue
        # Split on +| field separator
        fields = record.split("+|")
        writer.writerow(fields)

    with open(path, "w", encoding="utf-8") as f:
        f.write(output.getvalue())
    return True


if __name__ == "__main__":
    directory = os.getcwd()
    csv_files = sorted(f for f in os.listdir(directory) if f.endswith(".csv"))
    print(f"Converting {len(csv_files)} CSV files...")
    converted = skipped = cleared = 0
    for fname in csv_files:
        path = os.path.join(directory, fname)
        if fname in SKIP_TABLES:
            open(path, "w").close()  # truncate → COPY loads 0 rows
            cleared += 1
            print(f"  cleared    {fname} (binary table, not needed for spine)")
            continue
        result = convert_file(path)
        if result:
            converted += 1
            print(f"  converted  {fname}")
        else:
            skipped += 1
            print(f"  skipped    {fname} (already TSV)")
    print(f"Done: {converted} converted, {skipped} skipped, {cleared} cleared.")
