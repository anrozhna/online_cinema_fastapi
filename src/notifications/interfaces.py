from abc import ABC, abstractmethod


class EmailSenderInterface(ABC):

    @abstractmethod
    async def send_activation_email(self, email: str, activation_link: str) -> None:
        """
        Asynchronously send an account activation email.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The activation link to include in the email.
        """
        pass

    @abstractmethod
    async def send_activation_complete_email(self, email: str, login_link: str) -> None:
        """
        Asynchronously send an email confirming that the account has been activated.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        pass

    @abstractmethod
    async def send_password_reset_email(self, email: str, reset_link: str) -> None:
        """
        Asynchronously send a password reset request email.

        Args:
            email (str): The recipient's email address.
            reset_link (str): The password reset link to include in the email.
        """
        pass

    @abstractmethod
    async def send_password_reset_complete_email(
        self, email: str, login_link: str
    ) -> None:
        """
        Asynchronously send an email confirming that the password has been reset.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        pass

    @abstractmethod
    async def send_comment_reply_email(self, email: str, reply_text: str) -> None:
        """
        Asynchronously send a notification email when someone replies
        to the user's comment.

        Args:
            email (str): The recipient's email address.
            reply_text (str): The text of the reply to include in the email.
        """
        pass

    @abstractmethod
    async def send_movie_removed_from_carts_email(
        self, email: str, movie_name: str, cart_count: int
    ) -> None:
        """
        Asynchronously notify a moderator that a movie was deleted while
        present in one or more user carts.

        Args:
            email (str): The recipient's email address.
            movie_name (str): Title of the deleted movie.
            cart_count (int): Number of carts the movie was present in.
        """
        pass

    @abstractmethod
    async def send_order_items_excluded_email(
        self, email: str, excluded_movie_names: str
    ) -> None:
        """
        Asynchronously notify a user that some items were excluded from
        their order because they were already purchased or already in
        another pending order.

        Args:
            email (str): The recipient's email address.
            excluded_movie_names (str): Comma-separated titles of the
                excluded movies to include in the email.
        """
        pass

    @abstractmethod
    async def send_order_confirmation_email(
        self, email: str, order_id: int, movie_names: str
    ) -> None:
        """
        Asynchronously notify a user that their order payment was
        successful and the order is confirmed.

        Args:
            email (str): The recipient's email address.
            order_id (int): ID of the confirmed order.
            movie_names (str): Comma-separated titles of the movies in the order.
        """
        pass
