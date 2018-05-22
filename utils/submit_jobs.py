import os
import sys
import boto3

JOB_RETRY_ATTEMPTS = 3
LARGE_MEM_JOBS = ['block-groups', 'deploy_public_data']
JOB_QUEUE = os.getenv('JOB_QUEUE')
JOB_DEFINITION = os.getenv('JOB_DEFINITION')
CACHE_JOB_DEFINITION = os.getenv('CACHE_JOB_DEFINITION')

if __name__ == '__main__':
    client = boto3.client('batch')

    job_filenames = sys.argv[1:]
    batch_jobs = []
    for filename in job_filenames:
        job_kwargs = {
            'jobName': 'etl-job',
            'jobQueue': JOB_QUEUE,
            'jobDefinition': JOB_DEFINITION,
            'retryStrategy': {
                'attempts': JOB_RETRY_ATTEMPTS
            },
            'parameters': {
                'filename': filename
            }
        }

        # Override container memory for specific jobs
        if any([j in filename for j in LARGE_MEM_JOBS]):
            job_kwargs['containerOverrides'] = {'memory': 15000}

        res = client.submit_job(**job_kwargs)
        batch_jobs.append(res)

    if not (len(job_filenames) == 1 and job_filenames[0] in ['deploy_data', 'demographics']):
        client.submit_job(
            jobName='cache-job',
            jobQueue=JOB_QUEUE,
            jobDefinition=CACHE_JOB_DEFINITION,
            retryStrategy={'attempts': JOB_RETRY_ATTEMPTS},
            dependsOn=[{'jobId': j['jobId']} for j in batch_jobs]
        )
