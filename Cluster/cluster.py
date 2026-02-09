import numpy as np
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt

# Add path to context extraction folder
# sys.path.append(r"C:\BLS\EvalAI8\Context Extraction")
from ContextExtraction.keyword_filter import get_filtered_keywords_from_pdf

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_clusters(pdf_path, max_clusters=8, use_elbow=True):
    """
    Cluster filtered keywords using K-Means with silhouette score or elbow method.
    Expects keywords already filtered. Handles small keyword sets.
    """

    # Step 1: Get filtered keywords (already cleaned and filtered)
    filtered_keywords = get_filtered_keywords_from_pdf(pdf_path)

    if not filtered_keywords:
        print("No keywords found after filtering.")
        return {}

    print("\n=== FILTERED KEYWORDS USED FOR CLUSTERING ===")
    for kw in filtered_keywords:
        print(kw)

    # Step 2: Handle very small keyword sets
    if len(filtered_keywords) < 4:
        print("Not enough keywords to cluster. Returning all keywords as one cluster.")
        return {"Theme_1": filtered_keywords}

    # Step 3: Generate embeddings
    embeddings = embedding_model.encode(filtered_keywords)
    X = embeddings

    # Step 4: Determine optimal clusters
    silhouette_scores = {}
    inertias = {}

    for n in range(2, min(max_clusters, len(filtered_keywords)) + 1):
        kmeans = KMeans(n_clusters=n, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        inertias[n] = kmeans.inertia_
        try:
            score = silhouette_score(X, labels)
            silhouette_scores[n] = score
        except:
            continue

    # Step 5: Choose number of clusters
    if use_elbow:
        if len(inertias) < 2:
            optimal_clusters = 1
        else:
            drops = [inertias[i] - inertias[i+1] for i in range(2, len(inertias))]
            if not drops:
                optimal_clusters = list(inertias.keys())[0]
            else:
                optimal_clusters = list(inertias.keys())[np.argmax(drops)]
        print("\nElbow method suggests optimal clusters:", optimal_clusters)
    else:
        if silhouette_scores:
            optimal_clusters = max(silhouette_scores, key=silhouette_scores.get)
            print(f"\nSilhouette method suggests optimal clusters = {optimal_clusters} "
                  f"(score={silhouette_scores[optimal_clusters]:.4f})")
        else:
            optimal_clusters = 1
            print("Silhouette scores not available. Using 1 cluster.")

    # Step 6: Final KMeans clustering
    final_kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
    final_labels = final_kmeans.fit_predict(X)

    # Step 7: Build clusters dictionary
    clusters = {}
    for label, kw in zip(final_labels, filtered_keywords):
        clusters.setdefault(f"Theme_{label + 1}", []).append(kw)

    print("\n=== FINAL KEYWORD CLUSTERS ===")
    for theme, kws in clusters.items():
        print(f"{theme}: {kws}")

    return clusters

if __name__ == "__main__":
    # Replace this path with a real PDF
    test_pdf = r"C:\BLS\EvalAI8\Uploads\IJRAR1ARP035.pdf"
    clusters = get_clusters(test_pdf, max_clusters=8, use_elbow=True)
