from torch import nn, optim

from utils.train_constants import *
from dataset.FaceDataset import FaceDataset
from models.gan.Discriminator import Discriminator
from models.gan.Generator import Generator
from trainers.trainer import Trainer


class GANTrainer(Trainer):
    def __init__(self, G: Generator, D: Discriminator, dataset: FaceDataset, log_tag: str):
        super().__init__(log_tag, dataset)

        self.G = G
        self.D = D

        self.criterion = nn.BCELoss()
        self.optim_G = optim.Adam(params=self.G.parameters(), lr=0.00025, betas=(0.5, 0.999))
        self.optim_D = optim.Adam(params=self.D.parameters(), lr=0.0001, betas=(0.5, 0.999))

    def _run_batch(self, images: torch.Tensor, labels: torch.Tensor = None, iteration: int = 0) -> None:
        b_size = images.size(0)

        true_labels = torch.empty(size=(b_size,), device=DEVICE).normal_(mean=1, std=0.2)
        true_labels = torch.min(true_labels, torch.ones(b_size, device=DEVICE))

        fake_labels = torch.empty(size=(b_size,), device=DEVICE).normal_(mean=0, std=0.2)
        fake_labels = torch.max(fake_labels, torch.zeros(b_size, device=DEVICE))

        # Add noise to images
        images += 0.05 * torch.randn(size=(b_size, 3, 200, 200), device=DEVICE)

        ################
        # D Optimization
        ################

        self.D.zero_grad()

        prediction = self.D(images).view(-1)
        loss_real_D = self.criterion(prediction, true_labels)
        loss_real_D.backward()

        noise = torch.randn(size=(b_size, VAE_Z_SIZE), device=DEVICE)
        fake_images = self.G(noise) + 0.05 * torch.randn(size=(b_size, 3, 200, 200), device=DEVICE)

        prediction = self.D(fake_images.detach()).view(-1)
        loss_fake_D = self.criterion(prediction, fake_labels)
        loss_fake_D.backward()

        loss_D = loss_real_D + loss_fake_D

        self.optim_D.step()

        ################
        # G Optimization
        ################

        self.G.zero_grad()

        prediction = self.D(fake_images).view(-1)
        loss_G = self.criterion(prediction, true_labels)
        loss_G.backward()

        self.optim_G.step()

        self.writer.add_scalar('Generator Loss', loss_G, iteration)  # , tag=self.log_tag)
        self.writer.add_scalar('Discriminator Loss', loss_D, iteration)  # , tag=self.log_tag)

    def _init_model(self):
        # Send both networks to the corresponding device (GPU or CPU)
        self.G = self.G.to(device=DEVICE)
        self.D = self.D.to(device=DEVICE)

        # Set both networks in train mode
        self.G.train()
        self.D.train()

        # Initialize weights of both networks
        self.G.apply(GANTrainer.__weights_init)
        self.D.apply(GANTrainer.__weights_init)

    def _get_result_sample(self):
        self.G.eval()
        samples = []
        with torch.no_grad():
            for _ in range(9):
                noise = torch.randn(size=(1, VAE_Z_SIZE), device=DEVICE)
                output = self.G(noise).squeeze()
                fake_image = (output - output.min()) / (output.max() - output.min())
                samples.append(fake_image)
        self.G.train()
        return torch.stack(samples, dim=0)

    def _save_checkpoint(self, epoch: int):
        pass

    @staticmethod
    def __weights_init(m):
        class_name = m.__class__.__name__
        if class_name.find('Conv') != -1:
            nn.init.normal_(m.weight.data, 0.0, 0.02)
        elif class_name.find('BatchNorm') != -1:
            nn.init.normal_(m.weight.data, 1.0, 0.02)
            nn.init.constant_(m.bias.data, 0)
