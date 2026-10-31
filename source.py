import dlt

from dlt.sources.hubspot import hubspot


def run_hubspot_pipeline():

    print("Starting HubSpot ingestion...")

    # Create dlt pipeline
    pipeline = dlt.pipeline(
        pipeline_name="hubspot_pipeline",
        destination="filesystem",
        dataset_name="hubspot_data"
    )

    # Connect to HubSpot
    source = hubspot()

    # Select Contacts resource
    source = source.with_resources("contacts")

    # Extract and save as Parquet
    info = pipeline.run(
        source,
        loader_file_format="parquet"
    )

    print(info)


if __name__ == "__main__":
    run_hubspot_pipeline()