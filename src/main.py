import argparse
import os
import random
from datetime import datetime

import torch
from dotenv import load_dotenv
from torchvision import transforms

from utils.generate_images import generate_images
from utils.train_constants import IMG_SIZE, BATCH_SIZE
from dataset.FaceDataset import FaceDataset
from models.autoencoder.vae import VAE
from models.evolutionary.face_classifier import FaceClassifier
from models.evolutionary.genetic_algorithm import GeneticAlgorithm
from models.gan.Discriminator import Discriminator
from models.gan.Generator import Generator
from trainers.ga_trainer import GATrainer
from trainers.gan_trainer import GANTrainer
from trainers.vae_trainer import VAETrainer


def main(args):
    load_dotenv()

    if args.generate is None:
        # Set random seed for reproducibility
        manual_seed = random.randint(1, 1e10) if args.seed is None else args.seed
        print(f'Random Seed: {manual_seed}')

        random.seed(manual_seed)
        torch.manual_seed(manual_seed)

        log_tag = ('-'.join(str(datetime.now()).split()) + f'_{manual_seed}').replace(':', '-')
        if not os.path.exists(os.environ['CKPT_DIR']):
            os.mkdir(os.environ['CKPT_DIR'])

        transform = transforms.Compose([
            transforms.RandomHorizontalFlip(),
            transforms.RandomPerspective(distortion_scale=0.1),
            transforms.RandomRotation(degrees=5),
            transforms.Resize(size=(IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
        ])

        ################################
        # Using Genetic Algorithms (GAs)
        ################################

        if args.model == 'GA':
            # Create a model for classifying between Faces or Non-Faces.
            # We use the output of this model as the fitness function of our Genetic Algorithm.
            model: FaceClassifier = FaceClassifier()

            if args.pretrained is None:
                dataset = FaceDataset(root_positive=os.environ['DATASET_PATH'],
                                      root_negative=os.environ['CIFAR_PATH'],
                                      transform=transform)
                train_dataset, val_dataset = dataset.train_test_split(test_samples=BATCH_SIZE)

                model = FaceClassifier()
                trainer = GATrainer(model, log_tag=log_tag, train_dataset=train_dataset, val_dataset=val_dataset)
                trainer.train()
            else:
                # Load pretrained model from the checkpoints directory.
                path = os.path.join(os.environ['CKPT_DIR'], f'{args.pretrained}.pt')
                model_weights = torch.load(path)
                model.load_state_dict(model_weights)

            # Run Genetic Algorithm
            model.eval()
            with torch.no_grad():
                GA = GeneticAlgorithm(model, par=False, log_tag=log_tag)
                GA.run()

            return

        ##############################################
        # Using Generative Adversarial Networks (GANs)
        ##############################################

        transform = transforms.Compose([
            transforms.RandomHorizontalFlip(),
            transforms.RandomPerspective(distortion_scale=0.1, p=0.2),
            transforms.RandomRotation(degrees=10),
            transforms.Resize(size=(IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
        ])
        dataset = FaceDataset(os.environ['DATASET_PATH'], transform=transform)

        if args.model == 'GAN':
            G = Generator()
            D = Discriminator()
            trainer = GANTrainer(G=G, D=D, dataset=dataset, log_tag=log_tag)
            trainer.train()

            return

        ########################################
        # Using Variational Auto Encoders (VAEs)
        ########################################

        if args.model == 'VAE':
            model = VAE()
            train_dataset, val_dataset = dataset.train_test_split(test_samples=BATCH_SIZE)
            trainer = VAETrainer(model=model, log_tag=log_tag, train_dataset=train_dataset, val_dataset=val_dataset)
            trainer.train()
    else:
        model_class = Generator if args.model == 'GAN' else VAE
        generate_images(checkpoint=args.generate[0], samples=int(args.generate[1]), ModelClass=model_class)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GAN for Face Generation.')
    parser.add_argument('model', type=str, choices=['GA', 'VAE', 'GAN'],
                        help='Choose model between VAE and GAN')
    parser.add_argument('--pretrained', type=str, required=False,
                        help='')
    parser.add_argument('--generate', nargs=2, required=False,
                        help='Whether to generate a sample instead of training the model. '
                             'Need to specify the model file name located in folder `/checkpoints`. '
                             'You also need to specify the number of samples to generate')
    parser.add_argument('--seed', type=int, required=False,
                        help='Set manual random seed for reproducibility')

    print(parser.parse_args())
    main(parser.parse_args())
