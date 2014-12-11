library(ggplot2)

ignores <- c("friend.percent", "enemy.percent", "recipient")
lm.na.fields <- c("Comma", "Colon", "SemiC", "QMark", "Exclam", "Dash", "Quote", "Apostro", "Parenth", "AllPct", "OtherP", "they", "ipron", "Dic", "WC", "Segment")

ignore <- function(ds, ignores) {
  return(ds[, !(names(ds) %in% ignores)])
}

ds <- read.csv("stats-full.csv", sep="\t")

ds.melt <- melt(ds, c("recipient", "responded"))
p <- qplot(value, data=ds.melt) + facet_wrap(~ variable) + theme_minimal()
ggsave("distributions.png", plot=p)

ds.nafix <- ds

ds.nafix$match.percent[is.na(ds.nafix$match.percent)] <- mean(ds$match.percent, na.rm=TRUE)

ds.subset <- ignore(ds, lm.na.fields)

# LOTS of overlap. seems individual features rarely are strong influences.
# does this mean only interaction effects matter and/or exist?
feature.density.p <- qplot(value, data=ds.melt, color=as.factor(responded), geom="density") + facet_wrap(~ variable, scales="free") + theme_minimal() + theme(axis.ticks = element_blank(), axis.text.x = element_blank(), axis.ticks = element_blank(), axis.text.y = element_blank())
ggsave("feature-density.png", plot=feature.density.p)

sc1 <- anova(lm(responded ~  WPS, data=ds))
sc1.p <- qplot(WPS, data=ds, color=as.factor(responded), geom="density") + theme_minimal()

# these two look fairly inconclusive with the plots...
sc2 <- anova(lm(responded ~ we, data=ds))
sc2.p <- qplot(we, data=ds, color=as.factor(responded), geom="density") + theme_minimal()
sc3 <- anova(lm(responded ~ you, data=ds))
sc3.p <- qplot(you, data=ds, color=as.factor(responded), geom="density") + theme_minimal()
