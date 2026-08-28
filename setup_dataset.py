import os


def create_dataset_directories():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    training_dir = os.path.join(data_dir, 'training')
    testing_dir = os.path.join(data_dir, 'testing')

    os.makedirs(training_dir, exist_ok=True)
    os.makedirs(testing_dir, exist_ok=True)

    print(f"Dataset directories ready:\n - {training_dir}\n - {testing_dir}")


if __name__ == "__main__":
    create_dataset_directories()
