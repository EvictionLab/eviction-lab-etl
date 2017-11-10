import sys
import boto3


if __name__ == '__main__':
    client = boto3.client('batch')

    job_filenames = sys.argv[1:]
    batch_jobs = []
    for filename in job_filenames:
        job_kwargs = {
            'jobName': 'etl-job',
            'jobQueue': 'eviction-lab-etl-job-queue',
            'jobDefinition': 'eviction-lab-etl-job',
            'retryStrategy': {
                'attempts': 3
            },
            'parameters': {
                'filename': filename
            }
        }
        if len(batch_jobs):
            job_kwargs['dependsOn'] = [{'jobId': batch_jobs[-1]['jobId']}]
        res = client.submit_job(**job_kwargs)
        batch_jobs.append(res)

    client.submit_job(
        jobName='cache-job',
        jobQueue='eviction-lab-etl-job-queue',
        jobDefinition='etl-cache-invalidation-job',
        retryStrategy={'attempts': 1},
        dependsOn=[{'jobId': batch_jobs[-1]['jobId']}]
    )
