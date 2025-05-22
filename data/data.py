import torchvision as tv
import torch

def getData():
    train_data = tv.datasets.mnist.MNIST(
        root='data',
        train=True,
        download=True,
        transform=tv.transforms.Compose([
            tv.transforms.ToTensor()
        ])
    )

    test_data = tv.datasets.mnist.MNIST(
        root='data',
        train=False,
        download=True,
        transform=tv.transforms.Compose([
            tv.transforms.ToTensor()
        ])
    )

    X_train = train_data.data.numpy().reshape(-1, 28*28) / 255.0  # Flatten and normalize
    y_train = train_data.targets.numpy()

    # Convert test data to NumPy
    X_test = test_data.data.numpy().reshape(-1, 28*28) / 255.0
    y_test = test_data.targets.numpy()
    
    
    return X_train, y_train, X_test, y_test


if __name__ == "__main__":
    getData()