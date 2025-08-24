# trying to see how well classifying using keywords works
import os
from app.classify.classifier import classify_text

DATASET_DIR = "data/provided_dataset"

def main():
    correct = 0
    total = 0
    results = {}

    for folder in os.listdir(DATASET_DIR):
        folder_path = os.path.join(DATASET_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        true_label = folder.lower().replace(" ", "_") 
        results[true_label] = {"correct": 0, "total": 0}

        for filename in os.listdir(folder_path):
            if not filename.endswith(".pdf"):
                continue
            file_path = os.path.join(folder_path, filename)

            # For evaluation, just read raw text quickly
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            predicted = classify_text(text)

            total += 1
            results[true_label]["total"] += 1
            if predicted == true_label:
                correct += 1
                results[true_label]["correct"] += 1

    print(f"Overall accuracy: {correct}/{total} = {correct/total:.2%}")
    for label, r in results.items():
        acc = r["correct"] / r["total"] if r["total"] else 0
        print(f"{label}: {r['correct']}/{r['total']} = {acc:.2%}")

if __name__ == "__main__":
    main()
