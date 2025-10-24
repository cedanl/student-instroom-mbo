### Amir Khodaie ###
### Project: mbo instroomprognose ###
### Huidig bestand: Student count realiseren ###
### Datum bewerking: 18/09/2025 ### 

#### Clean the Global Environment ####

rm (list = ls())

#### Set the working directory ####

setwd("C:\\Users\\AmirK\\Documents\\GitHub\\mboprognose\\input")

#### Libraries ####
library(readr)
library(dplyr)
library(vroom)

#### Read in datafile ####

#df <- read.csv2("aanmeldingen_oktober_2024.csv", sep = ",", stringsAsFactors = FALSE)
df <- vroom::vroom("aanmeldingen_oktober_2024.csv", delim = ",")
df_orig <- df

# --- Filter only ENROLLED students ---
df <- df %>% filter(status == "ENROLLED")

# --- Derive 'Collegejaar' from 'schooljaar' ---
df$Collegejaar <- trimws(as.character(df$schooljaar))

# --- Remove rows with no value or invalid value in 'opleidingcode' ---
df <- df %>%
  filter(!is.na(opleidingcode) & grepl("^[0-9]+$", opleidingcode))

# --- Clean string columns for grouping ---
df$opleidingcode   <- trimws(as.character(df$opleidingcode))
df$leertrajectmbo  <- trimws(as.character(df$leertrajectmbo))
df$instellingserkenningscode <- trimws(as.character(df$instellingserkenningscode))

# --- Group and count students ---
# Explicitly count rows per group
aggregated_df <- df %>%
  dplyr::group_by(Collegejaar, opleidingcode, leertrajectmbo) %>%
  dplyr::summarize(aantal_studenten = dplyr::n())

# --- Save aggregated result ---
write.csv(aggregated_df, "../output/student_count.csv", row.names = FALSE)