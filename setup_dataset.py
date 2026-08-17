import os
import urllib.request
import zipfile

def create_sample_dataset():
    """
    Since the actual dataset was not provided in the environment,
    this script acts as a stub to create the directory structure 
    and prompt the user on how to use it, or download a small sample if needed.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    training_dir = os.path.join(data_dir, 'training')
    testing_dir = os.path.join(data_dir, 'testing')

    os.makedirs(training_dir, exist_ok=True)
    os.makedirs(testing_dir, exist_ok=True)
    
    print("Dataset directories created at:")
    print(f"- {training_dir}")
    print(f"- {testing_dir}")
    print("Please place the 40 training HTML files and 10 testing HTML files here.")

if __name__ == "__main__":
    create_sample_dataset()
