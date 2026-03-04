# pygame_chess_gui.py
import pygame
import requests
from io import BytesIO

# Optional: if you want background removal and have rembg installed,
# uncomment the import below. The loader has a fallback if rembg isn't installed.
try:
    import rembg
    REMBG_AVAILABLE = True
except Exception:
    REMBG_AVAILABLE = False

pygame.init()

WIDTH, HEIGHT = 1000, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Game")

font = pygame.font.Font(None, 20)
medium_font = pygame.font.Font(None, 40)
big_font = pygame.font.Font(None, 50)

clock = pygame.time.Clock()
FPS = 60

# Board / pieces state (lists hold piece names and locations as (x,y) with origin (0,0) at top-left)
white_pieces = ['rook', 'knight', 'bishop', 'king', 'queen', 'bishop', 'knight', 'rook',
                'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn']
white_locations = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0),
                   (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)]
black_pieces = ['rook', 'knight', 'bishop', 'king', 'queen', 'bishop', 'knight', 'rook',
                'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn']
black_locations = [(0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7),
                   (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6)]

captured_pieces_white = []
captured_pieces_black = []

# Turn-step machine:
# 0 - white's turn, no selection
# 1 - white's turn, piece selected
# 2 - black's turn, no selection
# 3 - black's turn, piece selected
turn_step = 0
selection = None
valid_moves = []

# Piece canonical order used for image arrays (must match all image lists)
piece_order = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king']

# Image URLs (6 black + 6 white). Make sure these are reachable; you can replace with local files.
image_urls = [
    # black pawn, rook, knight, bishop, queen, king
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025945/black_pawn.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025345/black_rook.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025947/black_knight.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025951/black_bishop.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025946/black_queen.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025948/black_king.png',
    # white pawn, rook, knight, bishop, queen, king
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025953/white_pawn.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025949/white_rook.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025325/white_knight.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025944/white_bishop.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025952/white_queen.png',
    'https://media.geeksforgeeks.org/wp-content/uploads/20240302025943/white_king.png',
]

# Helper: load image bytes, optional rembg removal with fallback
def load_image_from_url(url):
    resp = requests.get(url, timeout=10)
    data = resp.content
    # If rembg available try to remove background; fall back gracefully
    if REMBG_AVAILABLE:
        try:
            out = rembg.remove(data)
            return out
        except Exception:
            return data
    else:
        return data

# Load images (store both normal and small variants)
def load_images():
    imgs = []
    small_imgs = []
    sizes = {
        'pawn': (65, 65),
        'other': (80, 80),
        'small': (45, 45)
    }
    # load in order of image_urls
    for idx, url in enumerate(image_urls):
        try:
            raw = load_image_from_url(url)
            surf = pygame.image.load(BytesIO(raw)).convert_alpha()
        except Exception as e:
            # fallback: create a placeholder surface
            surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            surf.fill((200, 0, 0, 180))
            pygame.draw.circle(surf, (255, 255, 255), (40,40), 30)
        # choose size: pawns in file order are first and seventh in our list
        if idx % 6 == 0:  # pawn indices 0 and 6
            big = pygame.transform.smoothscale(surf, sizes['pawn'])
        else:
            big = pygame.transform.smoothscale(surf, sizes['other'])
        small = pygame.transform.smoothscale(surf, sizes['small'])
        imgs.append(big)
        small_imgs.append(small)
    return imgs, small_imgs

loaded_imgs, loaded_small_imgs = load_images()
# Build black and white lists aligned with piece_order:
# our image_urls are [black pawn, black rook, black knight, black bishop, black queen, black king,
#                    white pawn, white rook, white knight, white bishop, white queen, white king]
black_images = [
    loaded_imgs[0],  # pawn
    loaded_imgs[1],  # rook
    loaded_imgs[2],  # knight
    loaded_imgs[3],  # bishop
    loaded_imgs[4],  # queen
    loaded_imgs[5],  # king
]
white_images = [
    loaded_imgs[6],  # pawn
    loaded_imgs[7],  # rook
    loaded_imgs[8],  # knight
    loaded_imgs[9],  # bishop
    loaded_imgs[10], # queen
    loaded_imgs[11], # king
]
small_black_images = [
    loaded_small_imgs[0], loaded_small_imgs[1], loaded_small_imgs[2],
    loaded_small_imgs[3], loaded_small_imgs[4], loaded_small_imgs[5]
]
small_white_images = [
    loaded_small_imgs[6], loaded_small_imgs[7], loaded_small_imgs[8],
    loaded_small_imgs[9], loaded_small_imgs[10], loaded_small_imgs[11]
]

# flashing / game over state
counter = 0
winner = ''
game_over = False

# ---------- Drawing helpers ----------
SQUARE = 100
BOARD_ORIGIN = (0, 0)
SIDEBAR_X = 800

def board_to_pixel(pos):
    """pos is (x,y) where x and y in 0..7; returns top-left pixel (px,py)"""
    return pos[0] * SQUARE, pos[1] * SQUARE

def draw_board():
    # draw 8x8 checkerboard
    colors = [(232, 235, 239), (125, 135, 150)]  # light, dark
    for y in range(8):
        for x in range(8):
            rect = pygame.Rect(x * SQUARE, y * SQUARE, SQUARE, SQUARE)
            color = colors[(x + y) % 2]
            pygame.draw.rect(screen, color, rect)
    # grid lines
    for i in range(9):
        pygame.draw.line(screen, (0,0,0), (i * SQUARE, 0), (i * SQUARE, 8 * SQUARE), 2)
        pygame.draw.line(screen, (0,0,0), (0, i * SQUARE), (8 * SQUARE, i * SQUARE), 2)
    # sidebar
    pygame.draw.rect(screen, (30, 30, 30), (SIDEBAR_X, 0, WIDTH - SIDEBAR_X, HEIGHT))
    pygame.draw.rect(screen, (212,175,55), (SIDEBAR_X, 0, WIDTH - SIDEBAR_X, HEIGHT), 5)

    status_texts = [
        'White: Select a Piece to Move!',
        'White: Select a Destination!',
        'Black: Select a Piece to Move!',
        'Black: Select a Destination!'
    ]
    screen.blit(big_font.render(status_texts[turn_step], True, (0,0,0)), (10, 820))
    screen.blit(medium_font.render('FORFEIT', True, (0,0,0)), (SIDEBAR_X + 10, 820))

def draw_pieces():
    # draw white pieces
    for i, piece in enumerate(white_pieces):
        loc = white_locations[i]
        px, py = board_to_pixel(loc)
        idx = piece_order.index(piece)
        img = white_images[idx]
        # center for pawns slightly different size - using offsets
        offset_x = (SQUARE - img.get_width()) // 2
        offset_y = (SQUARE - img.get_height()) // 2
        screen.blit(img, (px + offset_x, py + offset_y))
        if turn_step < 2 and selection == i:
            pygame.draw.rect(screen, (200,0,0), (px+1, py+1, SQUARE-2, SQUARE-2), 3)
    # draw black pieces
    for i, piece in enumerate(black_pieces):
        loc = black_locations[i]
        px, py = board_to_pixel(loc)
        idx = piece_order.index(piece)
        img = black_images[idx]
        offset_x = (SQUARE - img.get_width()) // 2
        offset_y = (SQUARE - img.get_height()) // 2
        screen.blit(img, (px + offset_x, py + offset_y))
        if turn_step >= 2 and selection == i:
            pygame.draw.rect(screen, (0,0,200), (px+1, py+1, SQUARE-2, SQUARE-2), 3)

def draw_captured():
    # white captured (black taken by white) on left of sidebar
    for i, p in enumerate(captured_pieces_white):
        idx = piece_order.index(p)
        screen.blit(small_black_images[idx], (SIDEBAR_X + 25, 5 + i * 50))
    # black captured (white taken by black) on right of sidebar
    for i, p in enumerate(captured_pieces_black):
        idx = piece_order.index(p)
        screen.blit(small_white_images[idx], (SIDEBAR_X + 125, 5 + i * 50))

def draw_valid_moves(moves):
    color = (200, 0, 0) if turn_step < 2 else (0, 0, 200)
    for mv in moves:
        # mv is (x,y)
        center = (mv[0] * SQUARE + SQUARE // 2, mv[1] * SQUARE + SQUARE // 2)
        pygame.draw.circle(screen, color, center, 8)

def draw_check_indicator():
    # simple blinking rectangle around king if one of opponent moves attacks king square
    global counter
    if counter < 15:
        if 'king' in white_pieces:
            w_king_idx = white_pieces.index('king')
            king_loc = white_locations[w_king_idx]
            # if any black move can reach king_loc, flash
            for moves in black_options:
                if king_loc in moves:
                    pygame.draw.rect(screen, (150,0,0), (king_loc[0]*SQUARE+1, king_loc[1]*SQUARE+1, SQUARE-2, SQUARE-2), 5)
                    break
        if 'king' in black_pieces:
            b_king_idx = black_pieces.index('king')
            king_loc = black_locations[b_king_idx]
            for moves in white_options:
                if king_loc in moves:
                    pygame.draw.rect(screen, (0,0,150), (king_loc[0]*SQUARE+1, king_loc[1]*SQUARE+1, SQUARE-2, SQUARE-2), 5)
                    break

def draw_game_over():
    pygame.draw.rect(screen, (0,0,0), (200, 200, 400, 70))
    screen.blit(font.render(f'{winner} won the game!', True, (255,255,255)), (210,210))
    screen.blit(font.render('Press ENTER to Restart!', True, (255,255,255)), (210,240))


# ---------- Move generation and checks ----------
# (I kept your check_* functions largely intact, just moved them below and used them.)
def check_king(position, color):
    moves_list = []
    if color == 'white':
        enemies_list = black_locations
        friends_list = white_locations
    else:
        friends_list = black_locations
        enemies_list = white_locations
    targets = [(1, 0), (1, 1), (1, -1), (-1, 0), (-1, 1), (-1, -1), (0, 1), (0, -1)]
    for dx, dy in targets:
        target = (position[0] + dx, position[1] + dy)
        if 0 <= target[0] <= 7 and 0 <= target[1] <= 7 and target not in friends_list:
            moves_list.append(target)
    return moves_list

def check_bishop(position, color):
    moves_list = []
    if color == 'white':
        enemies_list = black_locations
        friends_list = white_locations
    else:
        friends_list = black_locations
        enemies_list = white_locations
    directions = [(1, -1), (-1, -1), (1, 1), (-1, 1)]
    for x, y in directions:
        chain = 1
        while True:
            target = (position[0] + chain * x, position[1] + chain * y)
            if not (0 <= target[0] <= 7 and 0 <= target[1] <= 7):
                break
            if target in friends_list:
                break
            moves_list.append(target)
            if target in enemies_list:
                break
            chain += 1
    return moves_list

def check_rook(position, color):
    moves_list = []
    if color == 'white':
        enemies_list = black_locations
        friends_list = white_locations
    else:
        friends_list = black_locations
        enemies_list = white_locations
    directions = [(0,1),(0,-1),(1,0),(-1,0)]
    for x, y in directions:
        chain = 1
        while True:
            target = (position[0] + chain * x, position[1] + chain * y)
            if not (0 <= target[0] <= 7 and 0 <= target[1] <= 7):
                break
            if target in friends_list:
                break
            moves_list.append(target)
            if target in enemies_list:
                break
            chain += 1
    return moves_list

def check_queen(position, color):
    return check_bishop(position, color) + check_rook(position, color)

def check_pawn(position, color):
    moves_list = []
    if color == 'white':
        # forward one
        if position[1] < 7 and (position[0], position[1]+1) not in white_locations and (position[0], position[1]+1) not in black_locations:
            moves_list.append((position[0], position[1]+1))
        # forward two from starting rank
        if position[1] == 1 and (position[0], position[1]+2) not in white_locations and (position[0], position[1]+2) not in black_locations:
            moves_list.append((position[0], position[1]+2))
        # captures
        for dx in (-1, 1):
            tgt = (position[0] + dx, position[1] + 1)
            if 0 <= tgt[0] <= 7 and 0 <= tgt[1] <= 7 and tgt in black_locations:
                moves_list.append(tgt)
    else:
        if position[1] > 0 and (position[0], position[1]-1) not in white_locations and (position[0], position[1]-1) not in black_locations:
            moves_list.append((position[0], position[1]-1))
        if position[1] == 6 and (position[0], position[1]-2) not in white_locations and (position[0], position[1]-2) not in black_locations:
            moves_list.append((position[0], position[1]-2))
        for dx in (-1, 1):
            tgt = (position[0] + dx, position[1] - 1)
            if 0 <= tgt[0] <= 7 and 0 <= tgt[1] <= 7 and tgt in white_locations:
                moves_list.append(tgt)
    return moves_list

def check_knight(position, color):
    moves_list = []
    if color == 'white':
        enemies_list = black_locations
        friends_list = white_locations
    else:
        friends_list = black_locations
        enemies_list = white_locations
    targets = [(1, 2), (1, -2), (2, 1), (2, -1), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]
    for dx, dy in targets:
        tgt = (position[0] + dx, position[1] + dy)
        if 0 <= tgt[0] <= 7 and 0 <= tgt[1] <= 7 and tgt not in friends_list:
            moves_list.append(tgt)
    return moves_list

def check_options(pieces, locations, turn):
    all_moves = []
    for i, piece in enumerate(pieces):
        loc = locations[i]
        if piece == 'pawn':
            moves = check_pawn(loc, turn)
        elif piece == 'rook':
            moves = check_rook(loc, turn)
        elif piece == 'knight':
            moves = check_knight(loc, turn)
        elif piece == 'bishop':
            moves = check_bishop(loc, turn)
        elif piece == 'queen':
            moves = check_queen(loc, turn)
        elif piece == 'king':
            moves = check_king(loc, turn)
        else:
            moves = []
        all_moves.append(moves)
    return all_moves

# initialize options
black_options = check_options(black_pieces, black_locations, 'black')
white_options = check_options(white_pieces, white_locations, 'white')

# ---------- Main loop ----------
run = True
while run:
    clock.tick(FPS)
    counter = (counter + 1) % 30
    screen.fill((60,60,60))

    draw_board()
    draw_pieces()
    draw_captured()

    if selection is not None:
        # show valid moves for selected piece
        valid_moves = white_options[selection] if turn_step < 2 else black_options[selection]
        draw_valid_moves(valid_moves)

    # draw check indicator
    draw_check_indicator()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not game_over:
            mx, my = event.pos
            board_x = mx // SQUARE
            board_y = my // SQUARE
            click_coords = (board_x, board_y)

            # click in sidebar FORFEIT area (approx)
            if mx >= SIDEBAR_X and my >= 800:
                # forfeit button clicked
                if turn_step <= 1:
                    winner = 'black'
                else:
                    winner = 'white'
                game_over = True
                break

            # ensure click inside board
            if not (0 <= board_x <= 7 and 0 <= board_y <= 7):
                continue

            if turn_step <= 1:
                # white to move
                if click_coords in white_locations:
                    sel_idx = white_locations.index(click_coords)
                    selection = sel_idx
                    turn_step = 1
                elif selection is not None:
                    # attempt move to a valid square
                    valid_moves = white_options[selection]
                    if click_coords in valid_moves:
                        # perform move
                        # handle capture
                        if click_coords in black_locations:
                            idx = black_locations.index(click_coords)
                            captured_pieces_white.append(black_pieces[idx])
                            # capture king --> win
                            if black_pieces[idx] == 'king':
                                winner = 'white'
                                game_over = True
                            black_pieces.pop(idx)
                            black_locations.pop(idx)
                        # move white piece
                        white_locations[selection] = click_coords
                        # update options after move
                        black_options = check_options(black_pieces, black_locations, 'black')
                        white_options = check_options(white_pieces, white_locations, 'white')
                        # switch turn
                        selection = None
                        turn_step = 2
            else:
                # black to move
                if click_coords in black_locations:
                    sel_idx = black_locations.index(click_coords)
                    selection = sel_idx
                    turn_step = 3
                elif selection is not None:
                    valid_moves = black_options[selection]
                    if click_coords in valid_moves:
                        if click_coords in white_locations:
                            idx = white_locations.index(click_coords)
                            captured_pieces_black.append(white_pieces[idx])
                            if white_pieces[idx] == 'king':
                                winner = 'black'
                                game_over = True
                            white_pieces.pop(idx)
                            white_locations.pop(idx)
                        black_locations[selection] = click_coords
                        black_options = check_options(black_pieces, black_locations, 'black')
                        white_options = check_options(white_pieces, white_locations, 'white')
                        selection = None
                        turn_step = 0

        if event.type == pygame.KEYDOWN and game_over:
            if event.key == pygame.K_RETURN:
                # reset to initial position
                white_pieces = ['rook', 'knight', 'bishop', 'king', 'queen', 'bishop', 'knight', 'rook',
                                'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn']
                white_locations = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0),
                                   (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)]
                black_pieces = ['rook', 'knight', 'bishop', 'king', 'queen', 'bishop', 'knight', 'rook',
                                'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn']
                black_locations = [(0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7),
                                   (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6)]
                captured_pieces_white.clear()
                captured_pieces_black.clear()
                selection = None
                turn_step = 0
                winner = ''
                game_over = False
                black_options = check_options(black_pieces, black_locations, 'black')
                white_options = check_options(white_pieces, white_locations, 'white')

    if winner:
        game_over = True
        draw_game_over()

    pygame.display.flip()

pygame.quit()
